import logging
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, SystemMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig

from core.ai.tools.afip import tool_emitir_comprobante_afip
from core.ai.tools.consultas_db import tool_consultar_entidad_financiera
from core.ai.state import AgentState
from core.ai.tools.reportes import tool_calcular_resumen_iva

logger = logging.getLogger("LANGGRAPH_AGENT")

# 1. Instanciamos los motores de razonamiento
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [tool_emitir_comprobante_afip, tool_consultar_entidad_financiera, tool_calcular_resumen_iva]
llm_with_tools = llm.bind_tools(tools) if tools else llm

summary_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

def chatbot_node(state: AgentState, config: RunnableConfig):
    """
    Nodo principal de inferencia.
    """
    try:
        messages = state["messages"]
        response = llm_with_tools.invoke(messages, config)
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"Fallo en la inferencia del LLM: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content="Ocurrió un error al procesar tu solicitud. Por favor, intentá nuevamente.")],
            "error_message": str(e)
        }

def summarize_conversation_node(state: AgentState, config: RunnableConfig):
    """
    Nodo de compresión (Fase 14.10).
    Resume los mensajes antiguos para evitar el desbordamiento de tokens y altos costos en OpenAI.
    """
    messages = state["messages"]
    summary = state.get("summary", "")

    # Dejamos los últimos 4 mensajes intactos (contexto inmediato)
    messages_to_summarize = messages[:-4]

    if not messages_to_summarize:
        return {}

    if summary:
        summary_prompt = (
            f"Este es el resumen de la conversación hasta ahora: {summary}\n\n"
            "Extendé el resumen incorporando la información de los siguientes mensajes nuevos. "
            "Mantenelo extremadamente conciso y retené únicamente datos duros (nombres, CUITs, montos, intenciones):"
        )
    else:
        summary_prompt = "Creá un resumen conciso de los siguientes mensajes, reteniendo solo datos duros (nombres, CUITs, montos, intenciones):"

    summary_messages = [SystemMessage(content=summary_prompt)] + messages_to_summarize
    response = summary_llm.invoke(summary_messages, config)

    delete_messages = [RemoveMessage(id=m.id) for m in messages_to_summarize if m.id]

    logger.info(f"🧹 [MEMORIA] Historial comprimido. Mensajes purgados: {len(delete_messages)}")

    return {
        "summary": response.content,
        "messages": delete_messages
    }

# 🌟 FIX ARQUITECTÓNICO: Ruteo explícito y determinista.
# Erradicamos dependencias mágicas (tools_condition) para controlar el flujo al 100%.
def router_node_decision(state: AgentState):
    """
    Evalúa el estado actual y decide el próximo nodo.
    """
    messages = state["messages"]
    last_message = messages[-1]

    # 1. Si el último mensaje es una invocación a un tool, ruteamos a las herramientas
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # 2. Si no hay tools que ejecutar, verificamos la presión de memoria
    if len(messages) > 6:
        return "summarize"

    # 3. Finalizamos el flujo si no hay acciones pendientes
    return END


def compile_financial_copilot(checkpointer=None):
    """
    Ensambla el grafo con el nodo de resumen dinámico y herramientas.
    """
    graph_builder = StateGraph(AgentState)

    # Añadimos los nodos principales
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("summarize", summarize_conversation_node)

    if tools:
        tool_node = ToolNode(tools=tools)
        graph_builder.add_node("tools", tool_node)
        # Después de usar un tool, volvemos obligatoriamente al chatbot para que analice el resultado
        graph_builder.add_edge("tools", "chatbot")

    # Inyectamos nuestro Router Maestro
    graph_builder.add_conditional_edges(
        "chatbot",
        router_node_decision,
        {
            "tools": "tools",
            "summarize": "summarize",
            END: END
        }
    )

    # Después de resumir, el flujo termina
    graph_builder.add_edge("summarize", END)

    graph_builder.add_edge(START, "chatbot")

    return graph_builder.compile(checkpointer=checkpointer)