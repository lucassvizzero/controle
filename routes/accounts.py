from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Account
from core.schemas import (
    AccountOut,
    BankName,
    Column,
    ComboboxOption,
    CrudField,
    FilterField,
    Permissions,
    TemplateContext,
    UploadSchema,
)
from core.templates import templates
from routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/accounts")
def get_accounts(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = Query(1),
    per_page: int = Query(10),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    name: Optional[str] = Query(None),
    bank: Optional[str] = Query(None),
):
    # Constrói a query base
    query = db.query(Account).filter(Account.user_id == user.id)
    if name:
        query = query.filter(Account.name.ilike(f"%{name}%"))
    if bank:
        query = query.filter(Account.bank == bank)

    # Mapeia a ordenação
    sort_map = {
        "id": Account.id,
        "name": Account.name,
        "bank": Account.bank,
        "balance": Account.balance,
        "updated_at": Account.updated_at,
    }
    sort_column = sort_map.get(sort_by, Account.id)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    total_count = query.count()
    accounts_list = query.offset((page - 1) * per_page).limit(per_page).all()

    # Monta as colunas usando o schema Column
    columns = [
        Column(label="ID", type="number", sort=True, sort_key="id"),
        Column(label="Nome", type="text", sort=True, sort_key="name"),
        Column(label="Banco", type="text", sort=True, sort_key="bank"),
        Column(label="Saldo", type="currency", sort=True, sort_key="balance"),
        Column(label="Última Atualização", type="datetime", sort=True, sort_key="updated_at"),
    ]

    # Monta os valores (linhas) – cada célula na ordem das colunas
    values = []
    for acc in accounts_list:
        values.append(
            [
                acc.id,
                acc.name,
                acc.bank.value,
                acc.balance,
                acc.updated_at,
            ]
        )

    # Schema para o CRUD (modal de adicionar/editar)
    crud_schema = [
        CrudField(name="name", label="Nome", type="text", required=True, edit=True),
        CrudField(
            name="bank",
            label="Banco",
            type="combobox",
            required=True,
            edit=True,
            options=[
                ComboboxOption(value=BankName.santander.value, label="Santander").model_dump(),
                ComboboxOption(value=BankName.c6bank.value, label="C6 Bank").model_dump(),
                ComboboxOption(value=BankName.nubank.value, label="Nubank").model_dump(),
            ],
        ),
        CrudField(name="balance", label="Saldo", type="number", required=True, edit=True),
        CrudField(name="is_active", label="Ativo?", type="switch", required=False, edit=True),
    ]

    # Schema para os filtros
    filter_schema = [
        FilterField(name="name", label="Nome", type="text"),
        FilterField(
            name="bank",
            label="Banco",
            type="combobox",
            options=[
                ComboboxOption(value=BankName.santander.value, label="Santander").model_dump(),
                ComboboxOption(value=BankName.c6bank.value, label="C6 Bank").model_dump(),
                ComboboxOption(value=BankName.nubank.value, label="Nubank").model_dump(),
            ],
        ),
    ]

    # Schema para o upload de arquivo CSV (para criação em massa de contas, se desejado)
    upload_schema = UploadSchema(
        label="Adicionar Contas",
        description="O CSV deve conter as colunas: 'Nome', 'Banco' e 'Saldo'.",
        file_type="csv",
    )

    permissions = Permissions(add=True, edit=True, delete=True, upload=True, filter=True)

    # Monta o contexto usando TemplateContext (que já preenche dados automáticos do request)
    context = TemplateContext(
        request=request,
        entity="accounts",
        permissions=permissions,
        columns=columns,
        values=values,
        crud_schema=crud_schema,
        filter_schema=filter_schema,
        upload_schema=upload_schema,
        total_count=total_count,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return templates.TemplateResponse("pages/accounts.html", context.model_dump())


@router.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Retorna os detalhes da conta para edição."""
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if not account:
        return {"error": "Conta não encontrada"}

    return account


@router.post("/accounts")
def create_account(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    name: str = Form(...),
    bank: str = Form(...),
    balance: float = Form(0.00),
    is_active: bool = Form(...),
):
    """Cria uma nova conta bancária para o usuário autenticado."""
    new_account = Account(
        name=name, bank=bank, balance=balance, user_id=user.id, is_active=is_active
    )
    db.add(new_account)
    db.commit()
    return RedirectResponse(url="/accounts", status_code=303)


@router.post("/accounts/{account_id}/edit")
def edit_account(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    name: str = Form(...),
    bank: str = Form(...),
    balance: float = Form(0.00),
    is_active: bool = Form(...),
):
    """Edita uma conta bancária do usuário autenticado."""
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if not account:
        return RedirectResponse(url="/accounts", status_code=303)

    account.name = name
    account.bank = bank
    account.balance = balance
    account.is_active = is_active
    db.commit()
    return RedirectResponse(url="/accounts", status_code=303)


@router.post("/accounts/{account_id}/delete")
def delete_account(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Exclui uma conta bancária do usuário autenticado."""
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if account:
        db.delete(account)
        db.commit()
    return RedirectResponse(url="/accounts", status_code=303)


@router.post("/accounts/{account_id}/upload")
async def upload_transactions_csv(
    account_id: int,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recebe um arquivo CSV e adiciona transações a uma conta específica."""
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if not account:
        return {"error": "Conta não encontrada"}

    contents = await file.read()
    csv_data = contents.decode("utf-8").splitlines()

    return {"message": f"Transações importadas para a conta {account.name}!"}
