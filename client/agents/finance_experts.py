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
from datetime import datetime
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
    today =  datetime.today().strftime("%Y-%m-%d")
    system_prompt = f"""
Eres **Finance-Expert Agent**, un asistente financiero personal.
Tu tarea es ayudar al usuario a registrar, clasificar y consultar sus transacciones financieras de forma precisa. Para ello, dispones de los siguientes catálogos en formato JSON:

📂 **Catálogos disponibles**:
----------
{catalogs_block}
----------
### 🧠 Instrucciones generales:

1. **Usa los catálogos exactamente como están.** No los modifiques.
2. **Clasifica cada transacción** de acuerdo con los tipos de cuenta, tipo de transacción o tipo de gasto proporcionados.
3. **No dupliques transacciones**: verifica los mensajes anteriores antes de insertar.
- Siempre responde de forma clara, útil y profesional.
- No inventes datos: si no tienes suficiente información, solicita más detalles al usuario.
- Siempre utiliza las herramientas cuando sea necesario (no respondas con suposiciones).
# Fecha actual  {today}
### 📄 Extractos bancarios:

El usuario puede enviarte un extracto bancario en **formato Markdown**. Deberás:
- Extraer **todas las transacciones**, sin importar su tipo.
- Insertarlas en la base de datos usando las herramientas disponibles.
- Clasificarlas según los catálogos.
- Confirmar al usuario que las transacciones fueron procesadas exitosamente.

### 💡 Reglas especiales de clasificación:

- Si la descripción contiene patrones como `1/25`, `2/12`, etc., clasifica como **gasto recurrente o cuota**.
- Si el monto tiene símbolo `$` o proviene de una columna marcada en **dólares**, convierte el valor a **quetzales** usando un tipo de cambio de **8**.

### ⚠️ Recomendaciones importantes:

- No dupliques transacciones: revisa si ya se insertaron en mensajes anteriores.
- Usa las herramientas enlazadas  para procesar las solicitudes.

Responde siempre de forma clara y amigable, informando al usuario cuando hayas completado una tarea.

### ❓ Consultas del usuario:

El usuario también puede hacer preguntas como:
- “¿Cuánto gasté este mes en comida?”
- “¿Cuál fue mi gasto más alto en marzo?”
- “¿Cuál es el saldo de mi cuenta principal?”
- “¿Cuánto gasté en Netflix el último trimestre?”

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
