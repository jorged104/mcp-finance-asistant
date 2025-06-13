from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

async def router_node(state: dict, config: RunnableConfig) -> dict:
    last_msg = state["messages"][-1].content.strip().lower()

    # Decide si es una ruta de archivo o pregunta directa
    if last_msg.endswith(".pdf") or last_msg.endswith(".png") or last_msg.endswith(".jpg"):
        return {"next": "ocr_node"}
    else:
        return {"next": "finance_qa"}
