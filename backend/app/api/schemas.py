"""Pydantic schemas cho API v1."""
from datetime import date, datetime
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    role_name: str
    department: str


class TourCreate(BaseModel):
    code: str = Field(min_length=3, max_length=30)
    name: str
    tour_type: str
    start_date: date
    end_date: date
    operator_id: int
    price_per_pax: float = 0
    fixed_cost: float = 0
    var_cost_per_pax: float = 0
    planned_pax: int = 0
    rest_stops: str = ""


class TourEdit(BaseModel):
    price_per_pax: float = 0
    fixed_cost: float = 0
    var_cost_per_pax: float = 0
    planned_pax: int = 0
    rest_stops: str = ""
    justification: str = ""


class TourClose(BaseModel):
    actual_revenue: float
    actual_cost: float
    promo_value: float = 0


class D7Decision(BaseModel):
    decision: str  # ghep | doi | huy | chay


class RequestCreate(BaseModel):
    tour_id: int
    customer_name: str = ""
    customer_phone: str = ""
    source: str = ""
    care_note: str = ""
    pax: int = 1
    campaign_code: str = ""
    promo_code: str = ""
    discount: float = 0


class ParamPropose(BaseModel):
    key: str
    value: str
    effective_from: date
    source: str = ""


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)
