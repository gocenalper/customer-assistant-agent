from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from api.model import UserMessage, LLMResponse, ApprovalDecision
from graph.agent import compile_graph, get_llm_response, resume_approval
from graph.checkpointer import open_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with open_checkpointer() as checkpointer:
        compile_graph(checkpointer)
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/chat")
async def chat(message: UserMessage) -> LLMResponse:
    return await get_llm_response(message.message)


@app.post("/chat/{thread_id}/approval")
async def approval(thread_id: str, decision: ApprovalDecision) -> LLMResponse:
    response = await resume_approval(thread_id, decision.approved)
    if response is None:
        raise HTTPException(status_code=404, detail="No refund is waiting for approval on this thread.")
    return response

