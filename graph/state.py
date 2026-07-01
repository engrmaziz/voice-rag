from typing import TypedDict

class GraphState(TypedDict):
    question: str
    chat_history: list
    documents: list
    generation: str
    retry_count: int
    sources: list
