import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Account, Card, Category, Transaction
from core.schemas import (
    CategoryType,
    Column,
    ComboboxOption,
    CrudField,
    FilterField,
    Permissions,
    TemplateContext,
    UploadField,
    UploadSchema,
)
from core.templates import templates
from core.utils import alert_error, alert_success
from routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/transactions")
def get_transactions(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = Query(1),
    per_page: int = Query(10),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    account_id: int | str = Query(None),
    card_id: int | str = Query(None),
    category_id: int | str = Query(None),
    due_day_start: str = Query(None),
    due_day_end: str = Query(None),
    paid_at_start: str = Query(None),
    paid_at_end: str = Query(None),
    category_type: str = Query(None),
):
    # Base query com joins para poder ordenar por campos relacionados
    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .outerjoin(Card, Transaction.card_id == Card.id)
        .filter(Transaction.user_id == user.id)
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if card_id:
        query = query.filter(Transaction.card_id == card_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if category_type:
        query = query.filter(Category.type == category_type)
    if due_day_start or due_day_end:
        if due_day_start:
            start_date = date.fromisoformat(due_day_start)
            query = query.filter(Transaction.due_day >= start_date)
        if due_day_end:
            end_date = date.fromisoformat(due_day_end)
            query = query.filter(Transaction.due_day <= end_date)
    if paid_at_start or paid_at_end:
        if paid_at_start:
            start_date = date.fromisoformat(paid_at_start)
            query = query.filter(Transaction.paid_at >= start_date)
        if paid_at_end:
            end_date = date.fromisoformat(paid_at_end)
            query = query.filter(Transaction.paid_at <= end_date)

    sort_map = {
        "id": Transaction.id,
        "account": Account.name,
        "category": Category.name,
        "card": Card.name,
        "description": Transaction.description,
        "value": Transaction.value,
        "due_day": Transaction.due_day,
        "paid_at": Transaction.paid_at,
    }
    sort_column = sort_map.get(sort_by, Transaction.id)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    total_count = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()

    columns = [
        Column(label="ID", type="number", sort=True, sort_key="id"),
        Column(label="Conta", type="text", sort=True, sort_key="account"),
        Column(label="Categoria", type="html", sort=True, sort_key="category"),
        Column(label="Cartão", type="text", sort=True, sort_key="card"),
        Column(label="Descrição", type="text", sort=True, sort_key="description"),
        Column(label="Valor", type="currency", sort=True, sort_key="value"),
        Column(label="Vencimento", type="date", sort=True, sort_key="due_day"),
        Column(label="Pago em", type="date", sort=True, sort_key="paid_at"),
    ]

    values = []
    for t in transactions:
        account_name = t.account.name if t.account else "N/A"
        if t.category and t.category.icon and t.category.color:
            category_html = (
                f"<i class='{t.category.icon} text-xl' style='color:{t.category.color}'></i>"
                f" {t.category.name}"
            )
        elif t.category:
            category_html = t.category.name
        else:
            category_html = "N/A"
        card_name = t.card.name if t.card else ""
        display_value = float(t.value)
        if t.category and t.category.type == CategoryType.expense:
            display_value = -display_value
        values.append(
            [
                t.id,
                account_name,
                category_html,
                card_name,
                t.description or "",
                display_value,
                t.due_day,
                t.paid_at,
            ]
        )

    # Schemas para CRUD e filtros
    account_options = [
        ComboboxOption(value=acc.id, label=acc.name).model_dump()
        for acc in db.query(Account).filter(Account.user_id == user.id).all()
    ]
    category_options = [
        ComboboxOption(value=cat.id, label=cat.name).model_dump()
        for cat in db.query(Category).filter(Category.user_id == user.id).all()
    ]
    card_options = [
        ComboboxOption(value=c.id, label=c.name).model_dump()
        for c in db.query(Card).filter(Card.user_id == user.id).all()
    ]

    crud_schema = [
        CrudField(
            name="account_id",
            label="Conta",
            type="combobox",
            required=True,
            edit=True,
            options=account_options,
        ),
        CrudField(
            name="category_id",
            label="Categoria",
            type="combobox",
            required=True,
            edit=True,
            options=category_options,
        ),
        CrudField(
            name="card_id",
            label="Cartão",
            type="combobox",
            required=False,
            edit=True,
            options=[{"value": "", "label": "Nenhum"}] + card_options,
        ),
        CrudField(name="description", label="Descrição", type="text", required=False, edit=True),
        CrudField(name="value", label="Valor", type="number", required=True, edit=True, min=0),
        CrudField(name="due_day", label="Vencimento", type="date", required=True, edit=True),
        CrudField(name="paid_at", label="Pago em", type="date", required=False, edit=True),
    ]

    filter_schema = [
        FilterField(
            name="account_id",
            label="Conta",
            type="combobox",
            options=account_options,
        ),
        FilterField(
            name="card_id",
            label="Cartão",
            type="combobox",
            options=card_options,
        ),
        FilterField(
            name="category_id",
            label="Categoria",
            type="combobox",
            options=category_options,
        ),
        FilterField(
            name="category_type",
            label="Tipo",
            type="combobox",
            options=[
                ComboboxOption(value=CategoryType.income.value, label="Receita"),
                ComboboxOption(value=CategoryType.expense.value, label="Despesa"),
            ],
        ),
        FilterField(name="due_day_start", label="Vencimento de", type="date"),
        FilterField(name="due_day_end", label="Vencimento até", type="date"),
        FilterField(name="paid_at_start", label="Pago de", type="date"),
        FilterField(name="paid_at_end", label="Pago até", type="date"),
    ]

    upload_schema = UploadSchema(
        label="Adicionar Transações",
        description=(
            "O CSV deve conter as colunas: category_id, description, value, due_day, paid_at"
            " (opcional)."
        ),
        file_type="csv",
        pre_fields=[
            UploadField(
                name="account_id",
                label="Conta",
                type="combobox",
                required=True,
                options=account_options,
            ),
            UploadField(
                name="card_id",
                label="Cartão",
                type="combobox",
                required=False,
                options=[{"value": "", "label": "Nenhum"}] + card_options,
            ),
        ],
    )

    permissions = Permissions(add=True, edit=True, delete=True, upload=True, filter=True)

    context = TemplateContext(
        request=request,
        entity="transactions",
        permissions=permissions,
        columns=columns,
        values=values,
        crud_schema=crud_schema,
        filter_schema=filter_schema,
        upload_schema=upload_schema,
        total_count=total_count,
    )
    return templates.TemplateResponse("pages/transactions.html", context.model_dump())


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    """Retorna os dados de uma transação para edição no modal."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        return {"error": "Transação não encontrada"}
    # Retorna sempre o valor absoluto, já que armazenamos como positivo.
    return {
        "account_id": transaction.account_id,
        "category_id": transaction.category_id,
        "card_id": transaction.card_id if transaction.card_id else "",
        "description": transaction.description or "",
        "value": float(transaction.value),
        "due_day": transaction.due_day.isoformat(),
        "paid_at": transaction.paid_at.isoformat() if transaction.paid_at else "",
    }


@router.post("/transactions")
def create_transaction(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    account_id: int = Form(...),
    category_id: int = Form(...),
    card_id: str = Form(None),
    description: str = Form(""),
    value: float = Form(...),
    due_day: date = Form(...),
    paid_at: str = Form(None),
):
    """Cria uma nova transação. O valor é sempre armazenado como positivo."""
    new_transaction = Transaction(
        user_id=user.id,
        account_id=account_id,
        category_id=category_id,
        card_id=int(card_id) if card_id and card_id.strip() else None,
        description=description,
        value=abs(value),  # Armazena sempre como positivo
        due_day=due_day,
        paid_at=date.fromisoformat(paid_at) if paid_at else None,
        is_recurring=False,
    )
    db.add(new_transaction)
    try:
        db.commit()
        alert_success(request, "Transação criada com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao criar transação: {str(e)}")
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/transactions/{transaction_id}/edit")
def edit_transaction(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    account_id: int = Form(...),
    category_id: int = Form(...),
    card_id: str = Form(None),
    description: str = Form(""),
    value: float = Form(...),
    due_day: date = Form(...),
    paid_at: str = Form(None),
):
    """Edita uma transação existente. O valor é sempre armazenado como positivo."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        alert_error(request, "Transação não encontrada")
        return RedirectResponse(url="/transactions", status_code=303)

    transaction.account_id = account_id
    transaction.category_id = category_id
    transaction.card_id = int(card_id) if card_id and card_id.strip() else None
    transaction.description = description
    transaction.value = abs(value)
    transaction.due_day = due_day

    if paid_at:
        try:
            transaction.paid_at = date.fromisoformat(paid_at)
        except ValueError:
            alert_error(request, "Formato inválido para data de pagamento")
            return RedirectResponse(url="/transactions", status_code=303)
    else:
        transaction.paid_at = None

    try:
        db.commit()
        alert_success(request, "Transação editada com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao editar transação: {str(e)}")
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/transactions/{transaction_id}/delete")
def delete_transaction(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Exclui uma transação."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        alert_error(request, "Transação não encontrada")
        return RedirectResponse(url="/transactions", status_code=303)
    try:
        db.delete(transaction)
        db.commit()
        alert_success(request, "Transação excluída com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao excluir transação: {str(e)}")
    return RedirectResponse(url="/transactions", status_code=303)


@router.post("/transactions/upload")
def upload_transactions(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    file: UploadFile = File(...),
    account_id: int = Form(...),
    card_id: str = Form(None),
):
    """
    Importa transações em massa via arquivo CSV.
    O CSV deve conter, em cada linha, os campos: category_id, description, value, due_day, paid_at (opcional).
    """
    try:
        contents = file.file.read().decode("utf-8")
        reader = csv.DictReader(StringIO(contents))
        new_transactions = []
        for row in reader:
            new_trans = Transaction(
                user_id=user.id,
                account_id=account_id,
                card_id=int(card_id) if card_id and card_id.strip() else None,
                category_id=int(row["category_id"]),
                description=row.get("description", ""),
                value=abs(float(row["value"])),
                due_day=date.fromisoformat(row["due_day"]),
                paid_at=date.fromisoformat(row["paid_at"]) if row.get("paid_at") else None,
                is_recurring=False,
            )
            new_transactions.append(new_trans)
        db.add_all(new_transactions)
        db.commit()
        alert_success(request, f"{len(new_transactions)} transações importadas com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao importar transações: {str(e)}")
    finally:
        file.file.close()
    return RedirectResponse(url="/transactions", status_code=303)
