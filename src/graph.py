from src.agents.PreMatchAgent import PreMatchAgent
from src.agents.LiveAgent import LiveAgent
from src.agents.PostMatchAgent import PostMatchAgent
from src.agents.ChatAgent import ChatAgent
from src.agents.PredictionAgent import PredictionAgent


def build_prematch_graph():
    return PreMatchAgent().build()


def build_live_graph():
    return LiveAgent().build()


def build_postmatch_graph():
    return PostMatchAgent().build()


def build_chat_graph():
    return ChatAgent().build()


def build_prediction_graph():
    return PredictionAgent().build()
