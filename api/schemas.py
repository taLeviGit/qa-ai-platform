from pydantic import BaseModel, Field, EmailStr, field_validator

# =========== Authorization ==================

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
# =========== Customers ==================
    
class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    age: int = Field(ge=18, le=120)
    
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value:str) -> str:
        return value.lower()
    
class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=18, le=120)
    
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str| None:
        return value.lower() if value else value
    
class Customer(CustomerCreate):
    id: int

# =========== Quotes ==================

class QuoteCreate(BaseModel):
    customer_id: int
    car_value: float = Field(gt=0, le=1_000_000)


class Quote(BaseModel):
    id: int
    customer_id: int
    car_value: float
    price: float
    currency: str = "ILS"
    created_at: str

# =========== Policies ==================

class PolicyCreate(BaseModel):
    quote_id: int


class Policy(BaseModel):
    id: int
    quote_id: int
    status: str