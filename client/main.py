from langgraph.graph import StateGraph, END
from agents.listener_agent import listener_node
from agents.writer_agent import writer_node
from agents.schemas import State  # si lo pusiste en otro archivo
from config import load_config  
from utils import printGraph
from langchain_core.language_models import BaseLanguageModel
    ## LLM 
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.user_info import user_info_node
from agents.ocr_agent import ocr_node
from langgraph.prebuilt import  ToolNode, tools_condition
from agents.finance_experts import make_finance_expert_node
from agents.rate_limited_tool_node import build_rate_limited_tool_node

async def  main():
    ## LOAD CONFIG   use : api_key = config["llm"]["api_key"]
    config = load_config()
    async with MultiServerMCPClient(
        {
            "finance": {
                "command": "node",
                "args": ["C:/Users/jdmonterroson/Documents/tempproyect/mcp-finance-asistant/servers/finance/build/finance.js"],
                "transport": "stdio",
                "env" : {"NOTION_TOKEN": "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",
                 "NOTION_DB_ACCOUNTS":"1cf764d59d8c80c0807ad9fb1510dcc7" ,
                 "NOTION_DB_TRANSACTIONS":"1cf764d59d8c8061b615c588e7380709"}
            }
        }
    ) as client:
        print("Connected to MCP server")
        tools = client.get_tools()
        resourses_list = await client.get_resources( server_name="finance")
        finances_string_resouses = [item.as_string() for item in resourses_list]

        llm = ChatOpenAI(
            model="gpt-4.1-2025-04-14",
            temperature=0,
            api_key=config["llm"]["api_key"]
        )
        #tool_node = ToolNode(tools=tools)
        
        llm_tools =llm.bind_tools(tools)
        builder = StateGraph(state_schema=State)  
        builder.add_node("fetch_user_info", user_info_node)
        builder.set_entry_point("fetch_user_info")
        orc_node_calleable = ocr_node(config["mistral"]["api_key"])
        builder.add_node("ocr_node", orc_node_calleable)
        finance_experts_node = make_finance_expert_node(
            llm_tools,
            finances_string_resouses,
        )
        builder.add_node("finance_expert", finance_experts_node)
       
        tool_node = build_rate_limited_tool_node(tools, min_interval=1.0)

        builder.add_node("tools" , tool_node)
        builder.add_edge("fetch_user_info", "ocr_node")

        builder.add_edge("ocr_node", 'finance_expert')
        builder.add_conditional_edges(
            "finance_expert",
            tools_condition,                  # <-- decide a partir del último mensaje
            {"tools": "tools", END: END},
        )
        builder.add_edge("tools", "finance_expert")


        graph = builder.compile()

        config = {"configurable": {"thread_id": "26" }}

        while True:
            # pedir la ruta sin bloquear el event-loop
            user_input = await asyncio.to_thread(input, "Write file name : ")

            if user_input.lower() in {"quit", "exit", "q"}:
                print("Goodbye!")
                break

            # grafo en modo streaming asíncrono
            async for event in graph.astream(
                {"messages": [("user", user_input)]},
                config,
                stream_mode="values",
            ):
                event["messages"][-1].pretty_print()




if __name__ == "__main__":
    import asyncio
    asyncio.run(main())