from langgraph.graph import StateGraph, END
from .nodes import State, generate, retry, decide

def build_app():
    graph = StateGraph(State)

    graph.add_node("generate", generate)
    graph.add_node("retry", retry)

    graph.set_entry_point("generate")

    graph.add_conditional_edges(
        "generate",
        decide,
        {
            "success": END,
            "retry": "retry",
            "fail": END
        }
    )

    graph.add_edge("retry", "generate")

    return graph.compile()