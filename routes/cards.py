from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Account, Card
from core.schemas import (
    BrandName,
    CardOut,
    Column,
    ComboboxOption,
    CrudField,
    FilterField,
    Permissions,
    TemplateContext,
)
from core.templates import templates
from routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/cards")
def get_cards(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = 1,
    per_page: int = 10,
    sort_by: str = "id",
    sort_order: str = "asc",
    account_id: int = Query(None, alias="f_account_id"),
    name: str = Query(None, alias="f_name"),
    brand: str = Query(None, alias="f_brand"),
):
    # Constrói a query base
    query = db.query(Card).filter(Card.user_id == user.id)
    if name:
        query = query.filter(Card.name.ilike(f"%{name}%"))
    if brand:
        query = query.filter(Card.brand == brand)
    if account_id:
        query = query.filter(Card.account_id == account_id)

    sort_map = {
        "id": Card.id,
        "name": Card.name,
        "brand": Card.brand,
        "due_day": Card.due_day,
        "close_day": Card.close_day,
        "updated_at": Card.updated_at,
    }
    sort_column = sort_map.get(sort_by, Card.id)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    total_count = query.count()
    cards = query.offset((page - 1) * per_page).limit(per_page).all()

    # Define as colunas para o datagrid usando o schema Column
    columns = [
        Column(label="ID", type="number", sort=True, sort_key="id"),
        Column(label="Nome", type="text", sort=True, sort_key="name"),
        Column(label="Bandeira", type="text", sort=True, sort_key="brand"),
        Column(label="Vencimento", type="number", sort=True, sort_key="due_day"),
        Column(label="Fechamento", type="number", sort=True, sort_key="close_day"),
        Column(label="Última Atualização", type="datetime-local", sort=True, sort_key="updated_at"),
    ]

    # Monta os valores (linhas) – cada célula na ordem das colunas
    values = []
    for card in cards:
        values.append(
            [
                card.id,
                card.name,
                str(card.brand.value).title() if card.brand else "N/A",
                card.due_day,
                card.close_day,
                card.updated_at,
            ]
        )

    # Opções para os campos do CRUD (usando ComboboxOption)
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    crud_schema = [
        CrudField(
            name="account_id",
            label="Conta",
            type="combobox",
            required=True,
            edit=True,
            options=[ComboboxOption(value=acc.id, label=acc.name).model_dump() for acc in accounts],
        ),
        CrudField(name="name", label="Nome", type="text", required=True, edit=True),
        CrudField(
            name="brand",
            label="Bandeira",
            type="combobox",
            required=True,
            edit=True,
            options=[
                ComboboxOption(value=BrandName.visa.value, label="Visa").model_dump(),
                ComboboxOption(value=BrandName.mastercard.value, label="MasterCard").model_dump(),
                ComboboxOption(
                    value=BrandName.american_express.value, label="American Express"
                ).model_dump(),
            ],
        ),
        CrudField(
            name="due_day", label="Dia de Vencimento", type="number", required=True, edit=True
        ),
        CrudField(
            name="close_day", label="Dia de Fechamento", type="number", required=True, edit=True
        ),
        CrudField(name="is_active", label="Ativo?", type="switch", required=False, edit=True),
    ]

    # Schema para os filtros
    filter_schema = [
        FilterField(
            name="account_id",
            label="Conta",
            type="combobox",
            options=[ComboboxOption(value=acc.id, label=acc.name).model_dump() for acc in accounts],
        ),
        FilterField(name="name", label="Nome", type="text"),
        FilterField(
            name="brand",
            label="Bandeira",
            type="combobox",
            options=[
                ComboboxOption(value=BrandName.visa.value, label="Visa").model_dump(),
                ComboboxOption(value=BrandName.mastercard.value, label="MasterCard").model_dump(),
                ComboboxOption(
                    value=BrandName.american_express.value, label="American Express"
                ).model_dump(),
            ],
        ),
    ]

    # Monta o contexto usando o TemplateContext (que já preenche dados do request)
    context = TemplateContext(
        request=request,
        entity="cards",
        permissions=Permissions(add=True, edit=True, delete=True, filter=True),
        columns=columns,
        values=values,
        crud_schema=crud_schema,
        filter_schema=filter_schema,
        total_count=total_count,
    )

    return templates.TemplateResponse("pages/cards.html", context.model_dump())


@router.get("/cards/{card_id}", response_model=CardOut)
def get_card(card_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Retorna os detalhes do cartão para edição."""
    card = db.query(Card).filter(Card.id == card_id, Card.user_id == user.id).first()
    if not card:
        return {"error": "Cartão não encontrado"}

    return card


@router.post("/cards")
def create_card(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    account_id: int = Form(...),
    name: str = Form(...),
    brand: str = Form(...),
    due_day: int = Form(...),
    close_day: int = Form(...),
):
    """Cria um novo cartão de crédito para o usuário autenticado."""
    new_card = Card(
        name=name,
        brand=brand,
        due_day=due_day,
        close_day=close_day,
        user_id=user.id,
        account_id=account_id,
    )
    db.add(new_card)
    db.commit()
    return RedirectResponse(url="/cards", status_code=303)


@router.post("/cards/{card_id}/edit")
def edit_card(
    request: Request,
    card_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    account_id: int = Form(...),
    name: str = Form(...),
    brand: str = Form(...),
    due_day: int = Form(...),
    close_day: int = Form(...),
):
    """Edita um cartão do usuário autenticado."""
    card = db.query(Card).filter(Card.id == card_id, Card.user_id == user.id).first()
    if not card:
        return RedirectResponse(url="/cards", status_code=303)

    card.account_id = account_id
    card.name = name
    card.brand = brand
    card.due_day = due_day
    card.close_day = close_day
    db.commit()
    return RedirectResponse(url="/cards", status_code=303)


@router.post("/cards/{card_id}/delete")
def delete_card(
    request: Request,
    card_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Exclui um cartão do usuário autenticado."""
    card = db.query(Card).filter(Card.id == card_id, Card.user_id == user.id).first()
    if card:
        db.delete(card)
        db.commit()
    return RedirectResponse(url="/cards", status_code=303)
