from pydantic import BaseModel


class Recommendation(BaseModel):
    id: str
    priority: str
    title: str
    description: str
    parameter: str
