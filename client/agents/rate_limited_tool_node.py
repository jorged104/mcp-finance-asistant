# ──────────────────────────────────────────────────────────────
#  rate_limited_tool_node.py
# ──────────────────────────────────────────────────────────────
import asyncio, time, json
from typing import List, Dict
from langchain_core.messages import ToolMessage, AIMessage
from langchain_core.tools import BaseTool

def build_rate_limited_tool_node(
    tools: List[BaseTool],
    min_interval: float = 1.0,        # ► segundos mínimos entre requests
):
    """Devuelve un nodo asíncrono que ejecuta los tool-calls de forma
    secuencial respetando el intervalo.

    Uso:
        tool_node = build_rate_limited_tool_node(finance_tools, min_interval=1)
        builder.add_node("tools", tool_node)
    """

    # ---  mapa nombre → tool ----------------------------------
    tools_by_name: Dict[str, BaseTool] = {t.name: t for t in tools}

    # guardamos el instante de la última llamada a cualquier tool
    last_call_ts = 0.0

    async def _node(state: Dict):
        nonlocal last_call_ts

        # 1️⃣  Tomamos el último mensaje del asistente
        if not state.get("messages"):
            return {}
        ai_msg: AIMessage = state["messages"][-1]

        # 2️⃣  ¿Pidió ejecutar herramientas?
        if not getattr(ai_msg, "tool_calls", None):
            return {}     # → no cambia el estado, seguimos en el grafo

        out_messages = []

        # 3️⃣  Ejecutamos *cada* tool-call de forma secuencial
        for call in ai_msg.tool_calls:
            name = call["name"]
            args = call["args"]

            # respetar ventana de tiempo para rate-limit
            elapsed = time.perf_counter() - last_call_ts
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            # buscar herramienta
            tool = tools_by_name[name]
            # ── invocación asíncrona ──
            result = await tool.ainvoke(args)

            # registrar hora de esta llamada
            last_call_ts = time.perf_counter()

            # 4️⃣  devolvemos un ToolMessage con el resultado
            out_messages.append(
                ToolMessage(
                    content=json.dumps(result),
                    name=name,
                    tool_call_id=call["id"],
                )
            )

        # 5️⃣  Mezclamos los nuevos mensajes en el estado
        return {"messages": out_messages}

    return _node
