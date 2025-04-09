from pydantic import BaseModel
from typing import Optional
from langgraph.graph.message import AnyMessage , add_messages
from typing_extensions import TypedDict, Annotated

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    nota: Optional[str] = None
    resumen: Optional[str] = None 
