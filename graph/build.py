import typing
from langgraph.graph import StateGraph, END
from graph.state import GraphState
from graph.nodes import (
    rewrite_query,
    hybrid_retrieve,
    rerank,
    grade_documents,
    decide_after_grading,
    generate,
    check_hallucination
)

workflow = StateGraph(GraphState)

workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("hybrid_retrieve", hybrid_retrieve)
workflow.add_node("rerank", rerank)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("check_hallucination", check_hallucination)

workflow.set_entry_point("rewrite_query")
workflow.add_edge("rewrite_query", "hybrid_retrieve")
workflow.add_edge("hybrid_retrieve", "rerank")
workflow.add_edge("rerank", "grade_documents")

workflow.add_conditional_edges(
    "grade_documents",
    decide_after_grading,
    {
        "rewrite_query": "rewrite_query",
        "generate": "generate"
    }
)

workflow.add_edge("generate", "check_hallucination")
workflow.add_edge("check_hallucination", END)

app_graph = workflow.compile()
