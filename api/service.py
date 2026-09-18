from fastapi import FastAPI
from api.model import UserMessage, LLMResponse
from graph.agent import get_llm_response

app = FastAPI()


@app.post("/chat")
async def chat(message: UserMessage) -> LLMResponse:
    response = await get_llm_response(message.message)
    return LLMResponse(response=response)

