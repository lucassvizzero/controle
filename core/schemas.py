import enum
from datetime import date, datetime
from typing import Any, List, Literal, Optional

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, model_validator


# 🔹 Token
class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):

    id: int
    name: str
    email: str
    username: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 🔹 Cartões e Contas - Enumeradores
class BrandName(str, enum.Enum):
    visa = "visa"
    mastercard = "mastercard"
    american_express = "american_express"


class BankName(str, enum.Enum):
    santander = "santander"
    nubank = "nubank"
    c6bank = "c6bank"


# 🔹 Cartão de Crédito
class CardOut(BaseModel):
    id: int
    user_id: int
    account_id: Optional[int]
    name: str
    brand: Optional[BrandName] = None
    due_day: int
    close_day: int
    credit_limit: Optional[float] = None
    is_active: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 🔹 Conta Bancária
class AccountOut(BaseModel):
    id: int
    name: str
    bank: BankName
    balance: float = 0.00
    is_active: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 🔹 Categorias
class CategoryType(str, enum.Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"


class CategoryOut(BaseModel):
    id: int
    name: str
    type: CategoryType
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryDetail(BaseModel):
    id: int
    name: str
    type: str
    subcategories_count: int
    subcategories: Optional[list] = None
    transactions_count: int
    transactions: Optional[list] = None


class BudgetOut(BaseModel):
    id: int
    category_id: int
    limit_value: float
    month: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionIndexOut(BaseModel):   
    id: Optional[int] = None
    category_name: str
    category_type: str
    category_icon: str
    category_color: str
    description: str
    value: float
    due_day: date
    paid_at: Optional[datetime] = None
    is_card_invoice: bool = False
    close_day: Optional[date] = None
    transactions: Optional[list] = None


class Permissions(BaseModel):
    add: bool = False
    edit: bool = False
    delete: bool = False
    detail: bool = False
    upload: bool = False
    filter: bool = False


class BaseField(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    type: Literal[
        # input types
        "checkbox",
        "color",
        "date",
        "email",
        "file",
        "image",
        "month",
        "number",
        "password",
        "tel",
        "text",
        "time",
        "week",
        # custom types
        "datetime",
        "switch",
        "combobox",
        "action",
        "html",
        "table",
        "currency",
        "icons",
    ]


class Column(BaseField):
    sort: bool = False
    sort_key: Optional[str] = None


class ComboboxOption(BaseModel):
    value: Any
    label: str


class CrudField(BaseField):
    required: Optional[bool] = False
    edit: Optional[bool] = False
    options: Optional[List[ComboboxOption]] = None


class FilterField(BaseField):
    options: Optional[List[ComboboxOption]] = None


class DetailField(BaseField):
    columns: Optional[List[Column]] = None  # table
    tab: Optional[str] = None
    header: Optional[bool] = False


class UploadField(BaseField):
    required: Optional[bool] = False
    options: Optional[List[ComboboxOption]] = None


class UploadSchema(BaseModel):
    label: str
    description: str
    file_type: str
    pre_fields: Optional[List[UploadField]] = None


class TemplateContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    request: Request
    entity: Literal["cards", "accounts", "categories", "budgets", "transactions"]
    permissions: Permissions = Field(default_factory=Permissions)
    columns: List[Column]
    values: List[List[Any]]

    crud_schema: Optional[List[CrudField]] = None
    detail_schema: Optional[List[DetailField]] = None
    filter_schema: Optional[List[FilterField]] = None
    upload_schema: Optional[UploadSchema] = None

    # Context Auto-Populated
    user: UserOut
    alerts: List[dict]
    page: int
    per_page: int
    total_count: int
    sort_by: str
    sort_order: str

    @model_validator(mode="before")
    @classmethod
    def populate_context(cls, values: dict) -> dict:
        """Populate context with user, alerts, page, per_page, sort_by and sort_order."""
        request = values.get("request")
        values["alerts"] = request.session.pop("alerts", [])
        values["user"] = UserOut.model_validate(request.state.user)
        values["page"] = int(request.query_params.get("page", 1))
        values["per_page"] = int(request.query_params.get("per_page", 10))
        values["sort_by"] = request.query_params.get("sort_by", "id")
        values["sort_order"] = request.query_params.get("sort_order", "asc")
        return values
