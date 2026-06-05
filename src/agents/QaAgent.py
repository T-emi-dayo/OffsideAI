from src.agents.BaseAgent import BaseAgent

class QaAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        
    def run(self):
        prompt = self.get_prompt()
        