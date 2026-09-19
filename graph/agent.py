import json
import uuid
from typing import Annotated

import httpx
from langchain_core.messages import AnyMessage, ToolMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import START
from langgraph.graph import StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt
from pydantic import BaseModel
from api.model import LLMResponse, RefundResponse
from clients import stock_service
from tools.toolset import TOOLSET

load_dotenv()

llm = ChatOpenAI(model="gpt-5-mini", temperature=0).bind_tools(TOOLSET)
system_message = "You are a helpful agent with a kind manner"
approval_pending_message = "İade talebiniz alındı ve operatör onayı bekliyor."

class State(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]

async def chat_model(state: State) -> dict:
    response = await llm.ainvoke(state.messages)
    return {"messages": [response]}

def current_refund(state: State) -> tuple[ToolMessage, RefundResponse] | None:
    """The initiate_refund result of the current tool round, if it succeeded."""
    for message in reversed(state.messages):
        if not isinstance(message, ToolMessage):
            break
        if message.name == "initiate_refund" and message.artifact:
            return message, RefundResponse.model_validate(message.artifact)
    return None

def route_refund(state: State) -> str:
    found = current_refund(state)
    status = found[1].status if found else None

    if status == "PENDING_APPROVAL":
        return "human_approval"
    if status in ("READY", "APPROVED"):
        return "execute_refund"
    return "chat_model"

async def transition_refund(state: State, transition) -> dict:
    """Replaces the tool result, so the model sees the refund's latest state."""
    message, refund = current_refund(state)
    try:
        data = (await transition(refund.refundRequestId)).model_dump(mode="json")
        content = json.dumps(data)
    except (httpx.HTTPError, ValueError):
        data = None
        content = json.dumps({
            "error": "refund_not_completed",
            "message": "İade işlemi tamamlanamadı.",
        }, ensure_ascii=False)

    return {"messages": [message.model_copy(update={"content": content, "artifact": data})]}

async def human_approval(state: State) -> dict:
    _, refund = current_refund(state)
    # The node restarts from the top on resume; keep side effects below this line.
    approved = interrupt(refund.model_dump(mode="json"))

    if approved:
        return await transition_refund(state, stock_service.approve_refund)
    return await transition_refund(state, stock_service.reject_refund)

async def execute_refund(state: State) -> dict:
    return await transition_refund(state, stock_service.execute_refund)

builder = StateGraph(State)

builder.add_node("chat_model", chat_model)
builder.add_node("tools", ToolNode(TOOLSET))
builder.add_node("human_approval", human_approval)
builder.add_node("execute_refund", execute_refund)

builder.add_edge(START, "chat_model")
builder.add_conditional_edges("chat_model", tools_condition)
builder.add_conditional_edges("tools", route_refund, ["chat_model", "human_approval", "execute_refund"])
builder.add_conditional_edges("human_approval", route_refund, ["chat_model", "execute_refund"])
builder.add_edge("execute_refund", "chat_model")

graph = None

def compile_graph(checkpointer: BaseCheckpointSaver) -> None:
    """Called from the API lifespan, once the checkpointer's connection pool is open."""
    global graph
    graph = builder.compile(checkpointer=checkpointer)

async def run_graph(graph_input: dict | Command, thread_id: str) -> LLMResponse:
    result = await graph.ainvoke(graph_input, {"configurable": {"thread_id": thread_id}})

    if result.get("__interrupt__"):
        return LLMResponse(
            response=approval_pending_message,
            thread_id=thread_id,
            pending_approval=result["__interrupt__"][0].value,
        )

    # /chat keeps no conversation memory, so a finished thread is never read again.
    await graph.checkpointer.adelete_thread(thread_id)
    return LLMResponse(response=result["messages"][-1].text, thread_id=thread_id)

async def get_llm_response(message: str) -> LLMResponse:
    return await run_graph({
        "messages": [
            ("system", system_message),
            ("human", message),
        ]
    }, str(uuid.uuid4()))

async def resume_approval(thread_id: str, approved: bool) -> LLMResponse | None:
    """Returns None when the thread has no refund waiting for approval."""
    snapshot = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    if not snapshot.interrupts:
        return None
    return await run_graph(Command(resume=approved), thread_id)
