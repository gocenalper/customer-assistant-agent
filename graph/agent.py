from typing import Annotated

from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langgraph.constants import START
from langgraph.graph import StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel

from tools.toolset import TOOLSET

load_dotenv()

llm = ChatOpenAI(model="gpt-5-mini", temperature=0).bind_tools(TOOLSET)
system_message = "You are a helpful agent with a kind manner"

class State(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]

async def chat_model(state: State) -> dict:
    response = await llm.ainvoke(state.messages)
    return {"messages": [response]}


builder = StateGraph(State)

builder.add_node("chat_model", chat_model)
builder.add_node("tools", ToolNode(TOOLSET))

builder.add_edge(START, "chat_model")
builder.add_conditional_edges("chat_model", tools_condition)
builder.add_edge("tools", "chat_model")

graph = builder.compile()

async def get_llm_response(message: str) -> str:
    result = await graph.ainvoke({
        "messages": [
            ("system", system_message),
            ("human", message),
        ]
    })

    return result["messages"][-1].text



