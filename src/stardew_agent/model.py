from stardew_agent.config import settings
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=settings.model,
    base_url=settings.base_url,
    api_key=settings.openai_api_key,
    temperature=0.5,
)
