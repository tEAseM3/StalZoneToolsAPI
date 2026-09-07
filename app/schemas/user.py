from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=55)
    password: str = Field(min_length=8, max_length=16)


class UserDisplay(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    user: UserDisplay
    access_token: str
    token_type: str = "bearer"
