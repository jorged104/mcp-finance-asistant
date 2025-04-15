from langgraph.graph import StateGraph, END
from agents.listener_agent import listener_node
from agents.writer_agent import writer_node
from agents.schemas import State  # si lo pusiste en otro archivo
from config import load_config  
from utils import printGraph
from langchain_core.language_models import BaseLanguageModel
## LLM 
from langchain_openai import ChatOpenAI

from agents.user_info import user_info_node
from agents.ocr_agent import ocr_node

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

#printGraph(graph)
#final_state = graph.invoke(State()) 
#print("Estado final:", final_state)

config = {"configurable": {"thread_id": "26" }}

while True:
    user_input = input("Write file name : ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    for event in graph.stream({"messages": [("user", user_input)]}, config, stream_mode="values"):
        event["messages"][-1].pretty_print()