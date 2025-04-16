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

async def  main():
    ## LOAD CONFIG   use : api_key = config["llm"]["api_key"]
    config = load_config()
    print(str(config["llm"]["api_key"]))
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0,
        api_key=config["llm"]["api_key"]
    )

    builder = StateGraph(state_schema=State)  
    builder.add_node("fetch_user_info", user_info_node)
    builder.set_entry_point("fetch_user_info")

    orc_node_calleable = ocr_node(config["mistral"]["api_key"])
    builder.add_node("ocr_node", orc_node_calleable)
    builder.add_edge("fetch_user_info", "ocr_node")


    builder.add_edge("ocr_node", END)

    graph = builder.compile()

    #MCP Agent
    

    async with MultiServerMCPClient(
        {
            "math": {
                "command": "uv",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["C:/Users/jdmonterroson/Documents/tempproyect/mcp-finance-asistant/servers/finance/build/finance.js"],
                "transport": "stdio",
                "env" : {"NOTION_TOKEN": "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",
                 "NOTION_DB_ACCOUNTS":"1cf764d59d8c80c0807ad9fb1510dcc7" ,
                 "NOTION_DB_TRANSACTIONS":"1cf764d59d8c8061b615c588e7380709"}
            }
        }
    ) as client:
        print("Connected to MCP server")
        print(client)
        print("Available tools:")
        print(client.get_tools())
    #printGraph(graph)
    #final_state = graph.invoke(State()) 
    #print("Estado final:", final_state)

    config = {"configurable": {"thread_id": "26" }}

    while False:
        user_input = input("Write file name : ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        for event in graph.stream({"messages": [("user", user_input)]}, config, stream_mode="values"):
            event["messages"][-1].pretty_print()
    
    
from contextlib import asynccontextmanager
@asynccontextmanager
async def make_graph():
    async with MultiServerMCPClient(
        {
            "math": {
                "command": "node",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["C:/Users/jdmonterroson/Documents/tempproyect/mcp-finance-asistant/servers/finance/build/finance.js"],
                "transport": "stdio",
                "env" : {"NOTION_TOKEN": "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",
                 "NOTION_DB_ACCOUNTS":"1cf764d59d8c80c0807ad9fb1510dcc7" ,
                 "NOTION_DB_TRANSACTIONS":"1cf764d59d8c8061b615c588e7380709"}
            }
        }
    ) as client:
        yield client

async def execution():
    print("Start Running")
    async with make_graph() as client:
        print("Connected to MCP server")
        print(client.get_tools())
        
        resourses_list = await client.get_resources( server_name="math")
        for item in resourses_list:
            print("Resource Name")
            print(item.source)
            print(item.as_string())
            print(item.metadata)



if __name__ == "__main__":
    import asyncio
    asyncio.run(execution())