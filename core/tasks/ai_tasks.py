import logging
import os
from celery import shared_task
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from core.tasks.celery_config import app
from config.config import settings
from core.ai.agent import compile_financial_copilot

logger = logging.getLogger("AI_WORKER")

# 1. Configuración de Conexión para la Memoria (Checkpointer)
db_user = os.getenv("DB_USER", getattr(settings, "DB_USER", "postgres"))
db_password = os.getenv("DB_PASSWORD", getattr(settings, "DB_PASSWORD", ""))
db_host = os.getenv("DB_HOST", getattr(settings, "DB_HOST", "pgbouncer"))
db_port = os.getenv("DB_PORT", getattr(settings, "DB_PORT", "5432"))

# Usamos psycopg puro sin dialecto de sqlalchemy
DB_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/conciliador_master"

@app.task(bind=True, name="core.tasks.ai_tasks.process_agent_message_task")
def process_agent_message_task(self, tenant_schema: str, entidad_id: int, user_id: str, thread_id: str, user_message: str):
    """
    Recibe la intención del usuario, inyecta el contexto Zero-Trust y ejecuta LangGraph.
    La conexión a PostgreSQL para la memoria persistente se abre y cierra por cada tarea,
    garantizando compatibilidad total con Celery Worker Processes.
    """
    # 🌟 FIX SEGURIDAD B2B: Aislamiento estricto de la memoria.
    # El thread_id pasa a ser la combinación del inquilino y el uuid del chat frontal.
    # Evita cruce de datos si dos usuarios mandan el mismo thread_id.
    secure_thread_id = f"{tenant_schema}__{thread_id}"

    logger.info(f"💬 [AGENT] Procesando hilo {secure_thread_id} | Entidad: {entidad_id}")

    # 1. Armamos la Configuración del Hilo
    config = {
        "configurable": {
            "thread_id": secure_thread_id,
            "tenant_schema": tenant_schema,
            "entidad_id": entidad_id,
            "user_id": user_id
        }
    }

    # 2. Inicializamos el estado del grafo
    input_state = {
        "messages": [HumanMessage(content=user_message)],
        "tenant_schema": tenant_schema,
        "entidad_id": entidad_id,
        "user_id": user_id
    }

    try:
        self.update_state(state='PROCESSING', meta={'progress': 10, 'message': "Despertando a la IA y cargando memoria..."})

        # 3. CONEXIÓN SEGURA A BASE DE DATOS PARA EL CHECKPOINTER
        with ConnectionPool(
            conninfo=DB_URL,
            min_size=1,  # 🌟 FIX: min_size debe ser <= max_size
            max_size=3,
            kwargs={"autocommit": True}
        ) as pool:

            checkpointer = PostgresSaver(pool)
            checkpointer.setup() # Asegura que las tablas existan (Idempotente)

            # Compilamos el grafo inyectándole el saver
            financial_copilot = compile_financial_copilot(checkpointer=checkpointer)

            self.update_state(state='PROCESSING', meta={'progress': 30, 'message': "Analizando tu consulta..."})

            # 4. Ejecución del Grafo con Streaming de Nodos
            final_state = None
            for chunk in financial_copilot.stream(input_state, config=config, stream_mode="updates"):

                # Emitimos Heartbeats según el nodo
                if "tools" in chunk:
                    self.update_state(state='PROCESSING', meta={'progress': 50, 'message': "Ejecutando acción en el ERP..."})
                elif "chatbot" in chunk:
                    self.update_state(state='PROCESSING', meta={'progress': 80, 'message': "Estructurando respuesta..."})

                final_state = chunk

            # 5. Extracción de la respuesta final del nodo chatbot
            if final_state and "chatbot" in final_state:
                respuesta_texto = final_state["chatbot"]["messages"][-1].content
            else:
                # Fallback de seguridad leyendo el estado general si algo falló
                estado_completo = financial_copilot.get_state(config).values
                respuesta_texto = estado_completo["messages"][-1].content

            # El pool se cierra al salir del 'with'
            return {"respuesta": respuesta_texto}

    except Exception as e:
        logger.error(f"Fallo en la ejecución del Agente: {e}", exc_info=True)
        raise Exception(f"[BUSINESS_LOGIC] El Copiloto encontró un error: {str(e)}")