from typing import Dict, Any
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage


def make_finance_classifier_node(llm: BaseLanguageModel, finance_catalog_json: list[str]):
    catalogs_block = "\n".join(finance_catalog_json)
    today = datetime.today().strftime("%Y-%m-%d")
    system_prompt = f"""Eres Finance-Expert-Classify, tu única tarea es recibir extractos bancarios en markdown, extraer todas las transacciones e insertarlas en la base de datos usando las herramientas conectadas.
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
"""

    async def finance_classifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = [SystemMessage(content=system_prompt)]

        if md := state.get("markdown"):
            messages.append(HumanMessage(content="### Extracto bancario:\n" + md.strip()))

        response = await llm.ainvoke(messages)

        return {
            "messages": [response]
        }

    return finance_classifier_node
