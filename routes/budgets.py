from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Budget, Category
from core.schemas import (
    BudgetOut,
    Column,
    ComboboxOption,
    CrudField,
    FilterField,
    Permissions,
    TemplateContext,
)
from core.templates import templates
from core.utils import alert_error, alert_success
from routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


def parse_month_input(month_str: str) -> date:
    possible_formats = ["%Y-%m", "%Y-%m-%d", "%m/%Y"]
    for fmt in possible_formats:
        try:
            return datetime.strptime(month_str, fmt).date()
        except ValueError:
            continue
    raise ValueError("Formato inválido para mês. Tente, por exemplo, '2023-05'.")


@router.get("/budgets")
def get_budgets(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = Query(1),
    per_page: int = Query(10),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    category_id: int = Query(None),
    month: str = Query(None),
):
    # Constrói a query base (faz join com Category para permitir ordenação por nome da categoria)
    query = (
        db.query(Budget)
        .filter(Budget.user_id == user.id)
        .join(Category, Budget.category_id == Category.id)
    )
    if category_id:
        query = query.filter(Budget.category_id == category_id)
    if month:
        try:
            month_date = parse_month_input(month)
            query = query.filter(Budget.month == month_date)
        except ValueError:
            alert_error(request, "Formato inválido para mês.")

    # Ordenação
    sort_map = {
        "id": Budget.id,
        "category_name": Category.name,
        "limit_value": Budget.limit_value,
        "month": Budget.month,
    }
    sort_column = sort_map.get(sort_by, Budget.id)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    total_count = query.count()
    budgets = query.offset((page - 1) * per_page).limit(per_page).all()

    # Definição das colunas usando o schema Column
    columns = [
        Column(label="ID", type="number", sort=True, sort_key="id"),
        Column(label="Categoria", type="html", sort=True, sort_key="category_name"),
        Column(label="Limite", type="currency", sort=True, sort_key="limit_value"),
        Column(label="Mês", type="month", sort=True, sort_key="month"),
    ]

    # Monta os valores
    values = []
    for b in budgets:
        cat = b.category
        if cat and cat.icon and cat.color:
            category_html = (
                f"<i class='{cat.icon} text-xl' style='color:{cat.color}'></i> {cat.name}"
            )
        elif cat:
            category_html = cat.name
        else:
            category_html = "N/A"
        month_str = b.month.strftime("%Y-%m") if isinstance(b.month, date) else str(b.month)
        values.append([b.id, category_html, b.limit_value, month_str])

    # Schema CRUD para criação/edição
    category_options = [
        ComboboxOption(value=c.id, label=c.name).model_dump()
        for c in db.query(Category).filter(Category.user_id == user.id).all()
    ]
    crud_schema = [
        CrudField(
            name="category_id",
            label="Categoria",
            type="combobox",
            required=True,
            edit=True,
            options=category_options,
        ),
        CrudField(name="limit_value", label="Limite", type="number", required=True, edit=True),
        CrudField(name="month", label="Mês (YYYY-MM)", type="month", required=True, edit=True),
    ]

    # Schema de filtros
    filter_schema = [
        FilterField(
            name="category_id",
            label="Categoria",
            type="combobox",
            options=category_options,
        ),
        FilterField(name="month", label="Mês (YYYY-MM)", type="month"),
    ]

    permissions = Permissions(add=True, edit=True, delete=True, filter=True)

    context = TemplateContext(
        request=request,
        entity="budgets",
        permissions=permissions,
        columns=columns,
        values=values,
        crud_schema=crud_schema,
        filter_schema=filter_schema,
        total_count=total_count,
    )
    return templates.TemplateResponse("pages/budgets.html", context.model_dump())


@router.get("/budgets/{budget_id}", response_model=BudgetOut)
def get_budget(budget_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Retorna o orçamento para edição no modal."""
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    if not budget:
        return {"error": "Orçamento não encontrado"}

    return {
        "category_id": budget.category_id,
        "limit_value": float(budget.limit_value),
        "month": budget.month.strftime("%Y-%m"),
    }


@router.post("/budgets")
def create_budget(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    category_id: int = Form(...),
    limit_value: float = Form(...),
    month: str = Form(...),
):
    """Cria um novo orçamento."""
    try:
        month_date = parse_month_input(month)
    except ValueError:
        alert_error(request, "Formato inválido. Tente YYYY-MM ou ex.: 05/2023.")
        return RedirectResponse(url="/budgets", status_code=303)

    new_budget = Budget(
        user_id=user.id,
        category_id=category_id,
        limit_value=limit_value,
        month=month_date,
    )
    db.add(new_budget)
    try:
        db.commit()
        alert_success(request, "Orçamento criado com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao criar orçamento: {str(e)}")

    return RedirectResponse(url="/budgets", status_code=303)


@router.post("/budgets/{budget_id}/edit")
def edit_budget(
    request: Request,
    budget_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    category_id: int = Form(...),
    limit_value: float = Form(...),
    month: str = Form(...),
):
    """Edita um orçamento existente."""
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    if not budget:
        alert_error(request, "Orçamento não encontrado.")
        return RedirectResponse(url="/budgets", status_code=303)

    try:
        month_date = parse_month_input(month)
    except ValueError:
        alert_error(request, "Formato inválido. Tente YYYY-MM ou ex.: 05/2023.")
        return RedirectResponse(url="/budgets", status_code=303)

    budget.category_id = category_id
    budget.limit_value = limit_value
    budget.month = month_date

    try:
        db.commit()
        alert_success(request, "Orçamento editado com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao editar orçamento: {str(e)}")

    return RedirectResponse(url="/budgets", status_code=303)


@router.post("/budgets/{budget_id}/delete")
def delete_budget(
    request: Request,
    budget_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Exclui um orçamento do usuário."""
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    if not budget:
        alert_error(request, "Orçamento não encontrado.")
        return RedirectResponse(url="/budgets", status_code=303)

    try:
        db.delete(budget)
        db.commit()
        alert_success(request, "Orçamento excluído com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao excluir orçamento: {str(e)}")

    return RedirectResponse(url="/budgets", status_code=303)
