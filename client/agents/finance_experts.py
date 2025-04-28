# agents/finance_expert.py
# -------------------------------------------------------------
#  Finance-Expert node
#
#  • Recibe las listas de recursos (accounts, typetransactions,
#    typespend) para incrustarlas en el prompt.
#  • El LLM YA VIENE con `.bind_tools(mcp_tools)` – por tanto, si
#    necesita registrar movimientos o consultar saldos simplemente
#    invocará esas tools (insert_transaction, get_balance, etc.).
#  • El nodo solo construye los mensajes y devuelve:
#        {"messages": [ai_message]}
#    — LangGraph ejecutará las tool-calls con tu ToolNode.
# -------------------------------------------------------------
from typing import List, Dict, Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage


def make_finance_expert_node(
    llm: BaseLanguageModel,
    finance_catalog_json: List[str],
):
    """
    Factory:  devuelve el callable que se añade al grafo.

    Ejemplo de uso en main:
        insert_tx_tool, clf_node = build_classifier_node(...)
        finance_expert_node = make_finance_expert_node(
            llm, ACCOUNTS, TX_TYPES, SPEND_TYPES
        )
        builder.add_node("finance_expert", finance_expert_node)
    """

    # ---------- 1) Prompt del sistema ----------
    catalogs_block = "\n".join(finance_catalog_json)
    system_prompt = f"""
Eres **Finance-ExpertGPT**, un asistente financiero personal.

A continuación encontrarás los catálogos JSON provistos por el MCP
(cuentas, tipos de transacción, tipos de gasto, etc.).  
Utilízalos tal cual para clasificar o validar los datos que el usuario
u otros nodos te envíen.  
NO modifiques estos catálogos; solo consúltalos cuando sea necesario.

Catálogos válidos:
----------
{catalogs_block}
----------

Haz las llamadas necesarias a las herramientas para insertar todas las transacciones a la base de datos. 
"""

    # ---------- 2) Nodo asíncrono ----------
    async def finance_expert_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza solo 'messages'; las tool-calls las ejecuta ToolNode."""
        messages = state.get("messages", []).copy()

        # Añadimos el system prompt AL INICIO de la lista
        messages.insert(0, SystemMessage(content=system_prompt))

        # Si existe markdown (viene del OCR) lo enviamos como contexto
        if md := state.get("markdown"):
           
            messages.append(
                HumanMessage(
                    content="### Extracto bancario (markdown)\n" + md.strip()
                )
            )

        print("Mensajes enviados al modelo:")
        for msg in messages:
            print(msg)
        # Llamamos al modelo (ya enlazado con tools)
        ai_msg =  await llm.ainvoke(messages)
        print(ai_msg)
        # Devolvemos solo el nuevo mensaje
        return {"messages": [ai_msg] }

    return finance_expert_node
