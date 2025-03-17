from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Category, Transaction
from core.schemas import (
    CategoryDetail,
    CategoryOut,
    CategoryType,
    Column,
    ComboboxOption,
    CrudField,
    DetailField,
    FilterField,
    Permissions,
    TemplateContext,
)
from core.templates import templates
from core.utils import alert_error, alert_success
from routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/categories")
def get_categories(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = Query(1),
    per_page: int = Query(10),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    name: str = Query(None, alias="f_name"),
    type_filter: str = Query(None, alias="f_type_filter"),
):
    # Constrói a query base para categorias "pais"
    query = db.query(Category).filter(Category.user_id == user.id, Category.parent_id == None)
    if name:
        query = query.filter(Category.name.ilike(f"%{name}%"))
    if type_filter:
        try:
            query = query.filter(Category.type == CategoryType(type_filter))
        except Exception:
            alert_error(request, "Tipo de categoria inválido.")

    # Ordenação
    sort_map = {
        "id": Category.id,
        "name": Category.name,
        "type": Category.type,
    }
    sort_column = sort_map.get(sort_by, Category.id)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    total_count = query.count()
    categories = query.offset((page - 1) * per_page).limit(per_page).all()

    # Monta as colunas usando os schemas (Column)
    columns = [
        Column(label="ID", type="number", sort=True, sort_key="id"),
        Column(label="Nome", type="html", sort=True, sort_key="name"),
        Column(label="Tipo", type="text", sort=True, sort_key="type"),
        Column(label="SubCategorias", type="number", sort=False),
        Column(label="Transações", type="number", sort=False),
    ]

    # Monta os valores
    values = []
    for cat in categories:
        name_html = (
            f"<i class='{cat.icon} text-xl' style='color:{cat.color}'></i> {cat.name}"
            if cat.icon and cat.color
            else cat.name
        )
        cat_type = "Receita" if cat.type == CategoryType.income else "Despesa"
        subcats = db.query(Category).filter(Category.parent_id == cat.id).all()
        transactions_count = db.query(Transaction).filter(Transaction.category_id == cat.id).count()
        for sub in subcats:
            transactions_count += (
                db.query(Transaction).filter(Transaction.category_id == sub.id).count()
            )
        values.append([cat.id, name_html, cat_type, len(subcats), transactions_count])

    # Cria o schema para o CRUD (para o modal de adicionar/editar)
    parent_options = [ComboboxOption(value="", label="Ninguém")]
    for c in (
        db.query(Category).filter(Category.user_id == user.id, Category.parent_id == None).all()
    ):
        parent_options.append(ComboboxOption(value=c.id, label=c.name))

    crud_schema = [
        CrudField(
            name="parent_id",
            label="SubCategoria de",
            type="combobox",
            required=True,
            edit=True,
            options=[option.model_dump() for option in parent_options],
        ),
        CrudField(name="name", label="Nome", type="text", required=True, edit=True),
        CrudField(
            name="type",
            label="Tipo",
            type="combobox",
            required=True,
            edit=True,
            options=[
                ComboboxOption(value=CategoryType.income.value, label="Receita").model_dump(),
                ComboboxOption(value=CategoryType.expense.value, label="Despesa").model_dump(),
            ],
        ),
        CrudField(name="icon", label="Ícone", type="icons", required=False, edit=True),
        CrudField(name="color", label="Cor", type="color", required=False, edit=True),
    ]

    # Cria o schema de filtros (FilterField)
    filter_schema = [
        FilterField(name="name", label="Nome", type="text"),
        FilterField(
            name="type_filter",
            label="Tipo",
            type="combobox",
            options=[
                ComboboxOption(value=CategoryType.income.value, label="Receita").model_dump(),
                ComboboxOption(value=CategoryType.expense.value, label="Despesa").model_dump(),
            ],
        ),
    ]

    # Cria o schema para os detalhes (DetailField)
    detail_schema = [
        DetailField(name="id", label="ID", type="number", header=True),
        DetailField(name="name", label="Nome", type="html", header=True),
        DetailField(name="type", label="Tipo", type="text", header=True),
        DetailField(
            name="subcategories_count",
            label="Quantidade SubCategorias",
            type="number",
            header=True,
        ),
        DetailField(
            name="transactions_count", label="Quantidade Transações", type="number", header=True
        ),
        DetailField(
            name="subcategories",
            label="Lista",
            type="table",
            columns=[
                Column(name="id", label="ID", type="number"),
                Column(name="name", label="Nome", type="text"),
                Column(name="type", label="Tipo", type="text"),
                Column(name="transactions", label="Transações", type="number"),
                Column(name="unlink", label="Desassociar", type="action"),
            ],
            tab="SubCategorias",
        ),
        DetailField(
            name="transactions",
            label="Lista",
            type="table",
            columns=[
                Column(name="category_name", label="Categoria", type="html"),
                Column(name="id", label="ID", type="number"),
                Column(name="account_name", label="Conta", type="text"),
                Column(name="card_name", label="Cartão", type="text"),
                Column(name="type", label="Tipo", type="text"),
                Column(name="description", label="Descrição", type="text"),
                Column(name="value", label="Valor", type="currency"),
            ],
            tab="Transações",
        ),
    ]

    # Monta o contexto usando o TemplateContext (que já faz o populate automático)
    context = TemplateContext(
        request=request,
        entity="categories",
        permissions=Permissions(add=True, edit=True, delete=True, detail=True, filter=True),
        columns=columns,
        values=values,
        crud_schema=crud_schema,
        detail_schema=detail_schema,
        filter_schema=filter_schema,
        total_count=total_count,
    )

    return templates.TemplateResponse("pages/categories.html", context.model_dump())


@router.get("/categories/{category_id}/details", response_model=CategoryDetail)
def get_category_details(
    category_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    """Retorna os detalhes da categoria"""
    category = (
        db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    )

    subcategories_list = [
        {
            "id": sub.id,
            "name": sub.name,
            "type": "Receita" if sub.type == CategoryType.income else "Despesa",
            "transactions": db.query(Transaction).filter(Transaction.category_id == sub.id).count(),
            "unlink": f"/categories/{sub.id}/unlink" if sub.parent_id else None,
        }
        for sub in category.subcategories
    ]

    transactions_list = [
        {
            "id": transaction.id,
            "account_name": transaction.account.name,
            "card_name": transaction.card.name if transaction.card else "",
            "category_name": (
                f"<i class='{transaction.category.icon} text-xl'"
                f" style='color:{transaction.category.color}'></i> {transaction.category.name}"
            ),
            "type": "Receita" if transaction.category.type == CategoryType.income else "Despesa",
            "description": transaction.description,
            "value": transaction.value,
        }
        for transaction in category.transactions
    ]
    for sub in category.subcategories:
        for transaction in sub.transactions:
            transactions_list.append(
                {
                    "id": transaction.id,
                    "account_name": transaction.account.name,
                    "card_name": transaction.card.name if transaction.card else "",
                    "category_name": (
                        f"<i class='{transaction.category.icon} text-xl'"
                        f" style='color:{transaction.category.color}'></i>"
                        f" {transaction.category.name}"
                    ),
                    "type": (
                        "Receita" if transaction.category.type == CategoryType.income else "Despesa"
                    ),
                    "description": transaction.description,
                    "value": transaction.value,
                }
            )

    name = f"<i class='{category.icon} text-xl' style='color:{category.color}'></i> {category.name}"

    return CategoryDetail(
        id=category.id,
        name=name,
        type="Receita" if category.type == CategoryType.income else "Despesa",
        subcategories_count=len(subcategories_list),
        subcategories=subcategories_list,
        transactions_count=len(category.transactions),
        transactions=transactions_list,
    )


@router.post("/categories/{category_id}/unlink")
def unlink_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Desassocia uma subcategoria da categoria pai."""
    category = (
        db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    )
    if not category:
        return {"error": "Categoria não encontrada"}

    category.parent_id = None
    db.commit()

    alert_success(request, "Subcategoria desassociada com sucesso")
    return RedirectResponse(url="/categories", status_code=303)


@router.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Retorna os detalhes da categoria para edição."""
    category = (
        db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    )
    if not category:
        return {"error": "Categoria não encontrada"}

    return category


@router.post("/categories")
def create_category(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    name: str = Form(...),
    type: str = Form(...),
    icon: str = Form(...),
    color: str = Form(...),
    parent_id: str = Form(None),
):
    """Cria uma nova categoria para o usuário autenticado."""
    parent_id = int(parent_id) if parent_id else None
    try:
        new_category = Category(
            name=name,
            type=CategoryType(type),
            icon=icon,
            color=color,
            user_id=user.id,
            parent_id=parent_id,
        )
        db.add(new_category)
        db.commit()
        alert_success(request, "Categoria cadastrada com sucesso")
    except Exception:
        alert_error(request, f"Erro ao cadastrar categoria: {str(e)}")
    return RedirectResponse(url="/categories", status_code=303)


@router.post("/categories/{category_id}/edit")
def edit_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    name: str = Form(...),
    type: str = Form(...),
    icon: str = Form(...),
    color: str = Form(...),
    parent_id: str = Form(None),
):
    """Edita uma categoria do usuário autenticado."""
    parent_id = int(parent_id) if parent_id else None
    category = (
        db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    )
    if not category:
        alert_error(request, "Categoria não encontrada")
        return RedirectResponse(url="/categories", status_code=303)

    if parent_id and parent_id == category.id:
        alert_error(request, "Uma categoria não pode ser subcategoria dela mesma")
        return RedirectResponse(
            url="/categories",
            status_code=303,
        )

    category.name = name
    category.type = CategoryType(type)
    category.icon = icon
    category.color = color
    category.parent_id = parent_id
    db.commit()
    alert_success(request, "Categoria editada com sucesso")
    return RedirectResponse(url="/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
def delete_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Exclui uma categoria do usuário autenticado."""
    category = (
        db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    )
    try:
        db.delete(category)
        db.commit()
        alert_success(request, "Categoria deletada com sucesso")
    except Exception as e:
        alert_error(request, f"Erro ao deletar categoria: {str(e)}")

    return RedirectResponse(url="/categories", status_code=303)
