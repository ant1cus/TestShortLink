from pydantic import BaseModel

class Link(BaseModel):
    id: int
    url: str
    param: str | None
    short_url: str
    create_time: float

class AddLink(BaseModel):
    error: bool
    text: str
    data: Link | str

class FullLink(BaseModel):
    error: bool
    text: str
    data: str