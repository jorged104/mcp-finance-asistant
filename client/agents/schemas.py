from pydantic import BaseModel
from typing import Optional
from langgraph.graph.message import AnyMessage , add_messages
from typing_extensions import TypedDict, Annotated

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    file_path: str
    extracted_text: str
    markdown: str
    movimientos: list
    productos_financieros: list
    next : Optional[str] = None