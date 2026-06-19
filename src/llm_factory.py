"""
Fabrique de modèles LLM et Embeddings.

Le reste du code ne connaît que BaseChatModel / Embeddings — jamais le provider.
Pour brancher un nouveau provider : ajouter un elif dans get_llm() et get_embeddings().
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.config import settings


def get_llm() -> BaseChatModel:
    if settings.llm_provider == "vertexai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            vertexai=True,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0,
        )
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=0,
        )
    else:
        raise ValueError(
            f"Provider LLM inconnu : '{settings.llm_provider}'. "
            "Valeurs acceptées : vertexai, openai"
        )


def get_embeddings() -> Embeddings:
    if settings.embedding_provider == "vertexai":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            vertexai=True,
            project=settings.vertex_project,
            location=settings.vertex_location,
        )
    elif settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
        )
    else:
        raise ValueError(
            f"Provider embeddings inconnu : '{settings.embedding_provider}'. "
            "Valeurs acceptées : vertexai, openai"
        )
