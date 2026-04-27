from typing import Annotated
from langgraph.graph import MessagesState
import operator


class AgentState(MessagesState):
    errors: Annotated[list[str], operator.add]

    # TODO: add project-specific state fields here
