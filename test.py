

from pydantic import BaseModel


class TestAIService(BaseModel):
    capital: str
    location: str
    president: str
    

def main():
    from src.services.AIService import AIService
    prompt = "You are an expert in world geography. Please provide the capital, location, and president of Spain."
    schema = TestAIService
    result = AIService().get_structured_output(prompt, schema, usage_metadata= True)
    print(result)

if __name__ == "__main__":
    main()