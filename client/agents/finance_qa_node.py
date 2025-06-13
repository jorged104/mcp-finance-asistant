from typing import Dict, Any
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage


def make_finance_qa_node(llm: BaseLanguageModel, finance_catalog_json: list[str]):
    catalogs_block = "\n".join(finance_catalog_json)
    today = datetime.today().strftime("%Y-%m-%d")

    system_prompt = f"""
Eres Finance-Expert-QA, un asistente especializado en responder preguntas financieras del usuario usando las herramientas disponibles.
Catálogos disponibles:
{catalogs_block}
Puedes responder cosas como:
- ¿Cuánto gasté este mes en transporte?
- ¿Cuál fue el gasto más alto en marzo?
- ¿Qué suscripciones tengo?
- ¿Cuál es el saldo de mi cuenta?
Siempre usa herramientas para responder. No inventes datos. Si necesitas más información, pídesela al usuario.
Fecha actual: {today}
"""

    async def finance_qa_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        
        # OPTIMIZACIÓN 1: Solo tomar los últimos N mensajes para mantener contexto relevante
        MAX_CONTEXT_MESSAGES = 8  # Aumentado para mantener secuencias completas
        recent_messages = messages[-MAX_CONTEXT_MESSAGES:] if len(messages) > MAX_CONTEXT_MESSAGES else messages
        
        # OPTIMIZACIÓN 2: Filtrar mensajes manteniendo secuencias válidas de tool_calls
        filtered_messages = [SystemMessage(content=system_prompt)]
        
        # Procesar mensajes manteniendo la secuencia AIMessage -> ToolMessage
        i = 0
        while i < len(recent_messages):
            msg = recent_messages[i]
            
            if isinstance(msg, HumanMessage):
                # Siempre incluir mensajes del usuario
                filtered_messages.append(msg)
                i += 1
                
            elif isinstance(msg, AIMessage):
                # Si el AIMessage tiene tool_calls, incluir junto con sus ToolMessages
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    filtered_messages.append(msg)
                    i += 1
                    
                    # Buscar los ToolMessages correspondientes
                    while i < len(recent_messages) and isinstance(recent_messages[i], ToolMessage):
                        filtered_messages.append(recent_messages[i])
                        i += 1
                else:
                    # AIMessage sin tool_calls, incluir normalmente
                    filtered_messages.append(msg)
                    i += 1
                    
            elif isinstance(msg, ToolMessage):
                # Skip ToolMessages huérfanos (sin AIMessage previo con tool_calls)
                print(f"⚠️  Saltando ToolMessage huérfano: {msg.content[:50]}...")
                i += 1
                
            else:
                # Otros tipos de mensaje, incluir
                filtered_messages.append(msg)
                i += 1
        
        # OPTIMIZACIÓN 3: Comprimir mensajes muy largos si es necesario
        compressed_messages = []
        for msg in filtered_messages:
            if isinstance(msg, (HumanMessage, AIMessage)) and hasattr(msg, 'content') and len(str(msg.content)) > 1000:
                # Comprimir mensajes muy largos manteniendo información clave
                content_str = str(msg.content)
                compressed_content = content_str[:400] + "...[resumido]..." + content_str[-200:]
                
                if isinstance(msg, HumanMessage):
                    compressed_messages.append(HumanMessage(content=compressed_content))
                elif isinstance(msg, AIMessage):
                    # Preservar tool_calls si existen
                    new_msg = AIMessage(content=compressed_content)
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        new_msg.tool_calls = msg.tool_calls
                    compressed_messages.append(new_msg)
            else:
                compressed_messages.append(msg)
        
        # Validar secuencia antes de enviar
        valid_messages = []
        for i, msg in enumerate(compressed_messages):
            if isinstance(msg, ToolMessage):
                # Verificar que el mensaje anterior sea AIMessage con tool_calls
                if i > 0 and isinstance(compressed_messages[i-1], AIMessage) and hasattr(compressed_messages[i-1], 'tool_calls'):
                    valid_messages.append(msg)
                else:
                    print(f"⚠️  Descartando ToolMessage inválido en posición {i}")
            else:
                valid_messages.append(msg)
        
        print(f"Mensajes enviados al modelo (optimizado): {len(valid_messages)} mensajes")
        for i, msg in enumerate(valid_messages):
            content_preview = str(getattr(msg, 'content', ''))[:100] if hasattr(msg, 'content') else str(msg)[:100]
            print(f"{i}: {type(msg).__name__}: {content_preview}...")
        
        ai_msg = await llm.ainvoke(valid_messages)
        return {"messages": [ai_msg]}

    return finance_qa_node