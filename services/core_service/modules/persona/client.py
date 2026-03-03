from langchain_google_genai import ChatGoogleGenerativeAI
from shared.utils.config import get_settings

settings = get_settings()

def get_gemini_client(model: str = settings.GEMINI_MODEL, temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=settings.GOOGLE_API_KEY,
        convert_system_message_to_human=True,
    )