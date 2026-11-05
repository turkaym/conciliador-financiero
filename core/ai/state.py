from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Usamos add_messages para que LangGraph sepa cómo anexar (o eliminar) mensajes en PostgreSQL
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Contexto Inyectado
    tenant_schema: str
    entidad_id: int
    user_id: str

    # Memoria a largo plazo comprimida
    summary: str

    # Metadatos de ejecución
    current_tool: str | None
    error_message: str | None