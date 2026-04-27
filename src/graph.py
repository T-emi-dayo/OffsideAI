from langgraph.graph import StateGraph, START, END
from src.schemas.state import AgentState


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # TODO: add nodes
    # graph.add_node("node_name", node_fn)

    # TODO: add edges
    # graph.add_edge(START, "node_name")
    # graph.add_edge("node_name", END)

    return graph.compile()
