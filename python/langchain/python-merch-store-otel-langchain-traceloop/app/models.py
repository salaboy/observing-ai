from pydantic import BaseModel


class MerchItem(BaseModel):
    project_name: str
    type: str  # "T-Shirt", "Socks", "Sticker"
    quantity: int
    price: float
    logo_url: str

    @property
    def display_name(self) -> str:
        return f"{self.project_name} {self.type}"


class OrderLine(BaseModel):
    project_name: str
    type: str
    quantity: int


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
