from langgraph.graph import StateGraph, END
from agents.listener_agent import listener_node
from agents.writer_agent import writer_node
from schemas import State  # si lo pusiste en otro archivo
from config import load_config  

## LOAD CONFIG   use : api_key = config["llm"]["api_key"]
config = load_config()



builder = StateGraph(state_schema=State)  # ✅ aquí usamos la clase
builder.add_node("listener", listener_node)
builder.add_node("writer", writer_node)
builder.set_entry_point("listener")
builder.add_edge("listener", "writer")
builder.add_edge("writer", END)

graph = builder.compile()
#final_state = graph.invoke(State()) 
#print("Estado final:", final_state)

config = {"configurable": {"thread_id": "26" }}

while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    for event in graph.stream({"messages": [("user", user_input)]}, config, stream_mode="values"):
        event["messages"][-1].pretty_print()