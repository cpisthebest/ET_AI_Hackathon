from langchain_ollama import ChatOllama
from app.config import settings

def llm():
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0,
        format="json"
    )
