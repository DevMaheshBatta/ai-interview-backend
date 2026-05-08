
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str    


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr

    model_config = {
        "from_attributes": True
    }    