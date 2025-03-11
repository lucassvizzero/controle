from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Budget, Category, Transaction
from core.schemas import CategoryType
from core.templates import templates
from core.utils import alert_error, alert_success, get_alerts
from routes.auth import get_current_user

month_translation = {
    "January": "Janeiro",
    "February": "Fevereiro",
    "March": "Março",
    "April": "Abril",
    "May": "Maio",
    "June": "Junho",
    "July": "Julho",
    "August": "Agosto",
    "September": "Setembro",
    "October": "Outubro",
    "November": "Novembro",
    "December": "Dezembro",
}

router = APIRouter(dependencies=[Depends(get_current_user)])


# Adiciona a função progress_color aos globals do Jinja para que ela fique disponível nos templates.
def progress_color(progress: float) -> str:
    """
    Retorna a cor da barra de progresso:
      - Para progress <= 100: interpolação de azul-claro até verde.
      - Para progress > 100: interpolação de verde até vermelho-escuro (limitado a 150%).
    """
    if progress <= 100:
        ratio = progress / 100
        # Azul claro (173,216,230) a Verde (0,255,0)
        r = round((1 - ratio) * 173 + ratio * 0)
        g = round((1 - ratio) * 216 + ratio * 255)
        b = round((1 - ratio) * 230 + ratio * 0)
        return f"rgb({r},{g},{b})"
    else:
        # Para progress acima de 100%, de verde (0,255,0) até vermelho escuro (139,0,0) em 150%
        excess = min(progress, 150) - 100  # limite máximo em 150%
        ratio = excess / 50
        r = round((1 - ratio) * 0 + ratio * 139)
        g = round((1 - ratio) * 255 + ratio * 0)
        b = 0
        return f"rgb({r},{g},{b})"


# Disponibiliza progress_color para os templates Jinja
templates.env.globals["progress_color"] = progress_color


def shift_month(year: int, month: int, delta: int):
    new_month = month + delta
    new_year = year
    if new_month < 1:
        new_month += 12
        new_year -= 1
    elif new_month > 12:
        new_month -= 12
        new_year += 1
    return new_year, new_month


def get_period_range(year: int, month: int):
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    start_date = date(prev_year, prev_month, 20)
    end_date = date(year, month, 19)
    return start_date, end_date


@router.get("/")
def get_index(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Query(None),
    month: int = Query(None),
    paid_page: int = Query(1),
    paid_per_page: int = Query(10),
    pending_page: int = Query(1),
    pending_per_page: int = Query(10),
):
    # Determina o "mês nominal" se não forem passados year e month
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month
        if today.day >= 20:
            year, month = shift_month(year, month, -1)

    start_date, end_date = get_period_range(year, month)

    # Obtém o nome do mês em inglês e traduz manualmente
    month_name = datetime(year, month, 1).strftime("%B/%Y").title()
    month_name = month_name.replace(
        month_name.split("/")[0], month_translation[month_name.split("/")[0]]
    )
    prev_year, prev_month = shift_month(year, month, -1)
    next_year, next_month = shift_month(year, month, 1)

    # Transações Efetuadas (pagas) com paginação
    paid_query = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .filter(Transaction.paid_at.isnot(None))
        .filter(Transaction.paid_at >= start_date, Transaction.paid_at <= end_date)
        .order_by(desc(Transaction.paid_at), desc(Transaction.updated_at))
    )
    total_paid = paid_query.count()
    transacoes_efetuada_all = paid_query.all()
    transacoes_efetuadas = (
        paid_query.offset((paid_page - 1) * paid_per_page).limit(paid_per_page).all()
    )

    # Transações Pendentes com paginação
    pending_query = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .filter(Transaction.due_day >= start_date, Transaction.due_day <= end_date)
        .filter(Transaction.paid_at.is_(None))
        .order_by(desc(Transaction.due_day))
    )
    total_pending = pending_query.count()
    transacoes_pendentes = (
        pending_query.offset((pending_page - 1) * pending_per_page).limit(pending_per_page).all()
    )

    # Resumos
    entrou = sum(t.value for t in transacoes_efetuada_all if t.category.type == CategoryType.income)
    saiu = sum(t.value for t in transacoes_efetuada_all if t.category.type == CategoryType.expense)
    sobrou = entrou - saiu

    # Orçamentos do "mês nominal"
    month_date = date(year, month, 1)
    budgets = db.query(Budget).filter(Budget.user_id == user.id, Budget.month == month_date).all()
    total_budget = sum(b.limit_value for b in budgets)
    total_spent = (
        db.query(func.coalesce(func.sum(Transaction.value), 0))
        .filter(
            Transaction.user_id == user.id,
            Transaction.category_id.in_([b.category_id for b in budgets]),
            Transaction.paid_at >= start_date,
            Transaction.paid_at <= end_date,
        )
        .scalar()
    )
    orcamento_percent = 0
    if total_budget > 0:
        orcamento_percent = round((total_spent / total_budget) * 100, 2)

    # Agrupar orçamentos por categoria pai (apenas categorias pais com orçamento, ou cujas subcategorias possuam orçamento)
    def get_root_category(cat: Category):
        while cat.parent is not None:
            cat = cat.parent
        return cat

    parent_map = defaultdict(lambda: {"cat": None, "budgets": []})
    for b in budgets:
        cat = b.category
        root = get_root_category(cat)
        spent_val = (
            db.query(func.coalesce(func.sum(Transaction.value), 0))
            .filter(
                Transaction.user_id == user.id,
                Transaction.category_id == cat.id,
                Transaction.paid_at >= start_date,
                Transaction.paid_at <= end_date,
            )
            .scalar()
        )
        spent_val = float(spent_val or 0.0)
        item_info = {
            "budget_id": b.id,
            "cat_id": cat.id,
            "cat_name": cat.name,
            "cat_icon": cat.icon,
            "cat_color": cat.color,
            "limit_value": float(b.limit_value),
            "spent_value": spent_val,
        }
        if parent_map[root.id]["cat"] is None:
            parent_map[root.id]["cat"] = root
        parent_map[root.id]["budgets"].append(item_info)

    budgets_parent_info = []
    for root_id, data in parent_map.items():
        root_cat = data["cat"]
        if not root_cat:
            continue
        items = data["budgets"]
        total_limit = sum(it["limit_value"] for it in items)
        total_spent_group = sum(it["spent_value"] for it in items)
        progress = 0 if total_limit <= 0 else round((total_spent_group / total_limit) * 100, 1)
        budgets_parent_info.append(
            {
                "root_id": root_cat.id,
                "root_name": root_cat.name,
                "root_icon": root_cat.icon,
                "root_color": root_cat.color,
                "items": items,
                "total_limit": total_limit,
                "total_spent": total_spent_group,
                "progress": progress,
                "bar_color": progress_color(progress),
            }
        )

    return templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "user": user,
            "alerts": get_alerts(request),
            "year": year,
            "month": month,
            "month_name": month_name,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "start_date": start_date,
            "end_date": end_date,
            "entrou": entrou,
            "saiu": saiu,
            "sobrou": sobrou,
            "orcamento_percent": orcamento_percent,
            "budgets_parent_info": budgets_parent_info,
            "transacoes_efetuadas": transacoes_efetuadas,
            "transacoes_pendentes": transacoes_pendentes,
            "total_paid": total_paid,
            "paid_page": paid_page,
            "paid_per_page": paid_per_page,
            "total_pending": total_pending,
            "pending_page": pending_page,
            "pending_per_page": pending_per_page,
            "current_date": date.today(),
        },
    )


@router.post("/transactions/{transaction_id}/mark_paid")
def mark_transaction_paid(
    transaction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        alert_error(request, "Transação não encontrada")
        return RedirectResponse(url="/", status_code=303)
    transaction.paid_at = date.today()
    db.commit()
    alert_success(request, "Transação marcada como paga!")
    return RedirectResponse(url="/", status_code=303)
