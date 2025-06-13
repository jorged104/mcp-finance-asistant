from langgraph.graph import StateGraph, END
from agents.schemas import State
from config import load_config  
from utils import printGraph
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.user_info import user_info_node
from agents.ocr_agent import ocr_node
from langgraph.prebuilt import ToolNode, tools_condition
from agents.finance_experts import make_finance_expert_node
from agents.rate_limited_tool_node import build_rate_limited_tool_node
from agents.router_node import router_node
from agents.finance_qa_node import make_finance_qa_node
from agents.finance_classifier_node import make_finance_classifier_node
from langgraph.checkpoint.memory import MemorySaver
import asyncio
import uuid

async def main():
    ## LOAD CONFIG
    config = load_config()
    
    async with MultiServerMCPClient(
        {
            "finance": {
                "command": "node",
                "args": ["C:/Users/jdmonterroson/Documents/tempproyect/mcp-finance-asistant/servers/finance/build/finance.js"],
                "transport": "stdio",
                "env": {
                    "NOTION_TOKEN": "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",
                    "NOTION_DB_ACCOUNTS": "1cf764d59d8c80c0807ad9fb1510dcc7",
                    "NOTION_DB_TRANSACTIONS": "1cf764d59d8c8061b615c588e7380709"
                }
            }
        }
    ) as client:
        print("Connected to MCP server")
        tools = client.get_tools()
        resourses_list = await client.get_resources(server_name="finance")
        finances_string_resouses = [item.as_string() for item in resourses_list]

        # OPTIMIZACIÓN: Usar modelo más económico para operaciones simples
        llm = ChatOpenAI(
            model="gpt-4o-mini",  # Más económico que gpt-4.1
            temperature=0,
            api_key=config["llm"]["api_key"]
        )
        
        # Para operaciones complejas, mantener modelo potente
        llm_complex = ChatOpenAI(
            model="gpt-4.1-2025-04-14",
            temperature=0,
            api_key=config["llm"]["api_key"]
        )
        
        llm_tools = llm.bind_tools(tools)
        llm_complex_tools = llm_complex.bind_tools(tools)

        # Create Nodes - usar modelo apropiado según complejidad
        ocr_node_calleable = ocr_node(config["mistral"]["api_key"])
        finance_classifier_node = make_finance_classifier_node(llm_tools, finances_string_resouses)
        finance_qa_node = make_finance_qa_node(llm_tools, finances_string_resouses)  # QA usa modelo ligero

        # Build the Graph
        builder = StateGraph(state_schema=State)
        
        # Add nodes to the graph
        builder.add_node("fetch_user_info", user_info_node)
        builder.set_entry_point("fetch_user_info")
        
        builder.add_node("finance_classifier", finance_classifier_node)
        builder.add_node("finance_qa", finance_qa_node)
        builder.add_node("ocr_node", ocr_node_calleable)
        builder.add_node("router_node", router_node)
        
        # OPTIMIZACIÓN: Diferentes intervalos según el tipo de herramientas
        tool_node = build_rate_limited_tool_node(tools, min_interval=0.5)  # Más rápido para clasificación
        tool_node_qa = build_rate_limited_tool_node(tools, min_interval=1.0)  # Normal para QA
        builder.add_node("tools", tool_node)
        builder.add_node("tools_qa", tool_node_qa)
        
        # Add edges
        builder.add_edge("fetch_user_info", "router_node")
        builder.add_conditional_edges(
            "router_node",
            lambda state: state["next"],
            {"ocr_node": "ocr_node", "finance_qa": "finance_qa"},
        )

        builder.add_edge("ocr_node", 'finance_classifier')
        builder.add_conditional_edges(
            "finance_classifier",
            tools_condition,
            {"tools": "tools", END: END},
        )
        builder.add_conditional_edges(
            "finance_qa",
            tools_condition,
            {"tools": "tools_qa", END: END},
        )
        builder.add_edge("tools", "finance_classifier")
        builder.add_edge("tools_qa", "finance_qa")

        # OPTIMIZACIÓN: Memoria con límite de tokens
        memory = MemorySaver()
        graph = builder.compile(checkpointer=memory)
        printGraph(graph)
        
        thread_id = str(uuid.uuid4())
        config_graph = {"configurable": {"thread_id": thread_id}}
        
        # OPTIMIZACIÓN: Contador de tokens para monitoreo
        total_tokens_used = 0
        conversation_count = 0

        print("🤖 Finance Assistant iniciado. Escribe 'quit' para salir.")
        print("💡 Tip: Para optimizar tokens, sé específico en tus preguntas.")
        
        while True:
            user_input = await asyncio.to_thread(
                input, 
                f"\n[Conversación #{conversation_count + 1}] Tu pregunta: "
            )

            if user_input.lower() in {"quit", "exit", "q"}:
                print(f"👋 ¡Hasta luego! Tokens aproximados usados: {total_tokens_used}")
                break

            conversation_count += 1
            
            # OPTIMIZACIÓN: Limpiar estado cada X conversaciones para evitar acumulación
            if conversation_count % 10 == 0:
                print("🧹 Limpiando historial para optimizar tokens...")
                thread_id = str(uuid.uuid4())
                config_graph = {"configurable": {"thread_id": thread_id}}

            try:
                async for event in graph.astream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config_graph,
                    stream_mode="values",
                ):
                    # Solo mostrar la respuesta final del asistente
                    last_message = event["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content:
                        print(f"🤖: {last_message.content}")
                        
                        # Estimación básica de tokens (aproximada)
                        estimated_tokens = len(last_message.content.split()) * 1.3
                        total_tokens_used += estimated_tokens
                        
            except Exception as e:
                print(f"❌ Error: {e}")
                print("Intenta reformular tu pregunta.")

if __name__ == "__main__":
    asyncio.run(main())