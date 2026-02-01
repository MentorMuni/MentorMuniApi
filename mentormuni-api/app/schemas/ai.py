from pydantic import BaseModel

class AIRequest(BaseModel):
    prompt: str
    use_case: str

class AIResponse(BaseModel):
    output: str