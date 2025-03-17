import calendar
import json
from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Budget, Card, Category, Transaction
from core.schemas import CategoryType, TransactionIndexOut
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

FIRST_DAY_OF_MONTH = 20
LAST_DAY_OF_MONTH = 19


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
    if FIRST_DAY_OF_MONTH > LAST_DAY_OF_MONTH:
        prev_year, prev_month = shift_month(year, month, -1)
        _, last_day = calendar.monthrange(prev_year, prev_month)
        start_date = date(
            prev_year,
            prev_month,
            FIRST_DAY_OF_MONTH if FIRST_DAY_OF_MONTH <= last_day else last_day,
        )
    else:
        _, last_day = calendar.monthrange(year, month)
        start_date = date(
            year, month, FIRST_DAY_OF_MONTH if FIRST_DAY_OF_MONTH <= last_day else last_day
        )

    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, LAST_DAY_OF_MONTH if LAST_DAY_OF_MONTH <= last_day else last_day)
    return start_date, end_date


def convert_index_transactions(transactions):
    cards = {}
    remake_transactions = []
    for t in transactions:
        if t.card_id:
            if t.card_id not in cards:
                cards[t.card_id] = {
                    "card_id": t.card_id,
                    "card_name": t.card.name,
                    "card_brand": t.card.brand,
                    "card_due_day": t.card.due_day,
                    "card_close_day": t.card.close_day,
                    "transactions": [],
                }
            cards[t.card_id]["transactions"].append(
                TransactionIndexOut(
                    id=t.id,
                    category_name=t.category.name,
                    category_type=t.category.type,
                    category_icon=t.category.icon,
                    category_color=t.category.color,
                    description=t.description,
                    value=t.value,
                    due_day=t.due_day,
                    paid_at=t.paid_at,
                    is_card_invoice=False,
                    transactions=None,
                )
            )
        else:
            remake_transactions.append(
                TransactionIndexOut(
                    id=t.id,
                    category_name=t.category.name,
                    category_type=t.category.type,
                    category_icon=t.category.icon,
                    category_color=t.category.color,
                    description=t.description,
                    value=t.value,
                    due_day=t.due_day,
                    paid_at=t.paid_at,
                    is_card_invoice=False,
                    transactions=None,
                )
            )
    card_invoices = []

    for card in cards.values():
        card["transactions"] = sorted(card["transactions"], key=lambda t: t.due_day)
        tmp_card_invoices = {}
        for card_transaction in card["transactions"]:
            month_card = card_transaction.due_day.month
            year_card = card_transaction.due_day.year
            if card_transaction.due_day.day > card["card_close_day"]:
                year_card, month_card = shift_month(
                    card_transaction.due_day.year, card_transaction.due_day.month, 1
                )

            _, last_day = calendar.monthrange(year_card, month_card)
            due_day = date(
                year_card,
                month_card,
                card["card_due_day"] if card["card_due_day"] <= last_day else last_day,
            )
            close_day = date(
                year_card,
                month_card,
                card["card_close_day"] if card["card_close_day"] <= last_day else last_day,
            )
            month_card_name = due_day.strftime("%B/%Y").title()
            month_card_name = month_card_name.replace(
                month_card_name.split("/")[0], month_translation[month_card_name.split("/")[0]]
            )

            if card_transaction.paid_at:
                if month_card_name + "-paid" not in tmp_card_invoices:
                    tmp_card_invoices[month_card_name + "-paid"] = TransactionIndexOut(
                        category_name="Fatura",
                        category_type="expense",
                        category_icon="fas fa-credit-card",
                        category_color="#FF5722",
                        description=f"Fatura {card['card_name']} - {month_card_name}",
                        value=card_transaction.value,
                        due_day=due_day,
                        close_day=close_day,
                        paid_at=card_transaction.paid_at,
                        is_card_invoice=True,
                        transactions=[json.loads(card_transaction.model_dump_json())],
                    )
                else:
                    tmp_card_invoices[month_card_name + "-paid"].value += card_transaction.value
                    tmp_card_invoices[month_card_name + "-paid"].transactions.append(
                        json.loads(card_transaction.model_dump_json())
                    )
            else:
                if month_card_name not in tmp_card_invoices:
                    tmp_card_invoices[month_card_name] = TransactionIndexOut(
                        category_name="Fatura",
                        category_type="expense",
                        category_icon="fas fa-credit-card",
                        category_color="#FF5722",
                        description=f"Fatura {card['card_name']} - {month_card_name}",
                        value=card_transaction.value,
                        due_day=due_day,
                        close_day=close_day,
                        paid_at=None,
                        is_card_invoice=True,
                        transactions=[json.loads(card_transaction.model_dump_json())],
                    )
                else:
                    tmp_card_invoices[month_card_name].value += card_transaction.value
                    tmp_card_invoices[month_card_name].transactions.append(
                        json.loads(card_transaction.model_dump_json())
                    )
        card_invoices += list(tmp_card_invoices.values())
    return card_invoices + remake_transactions


def make_pagination(transacoes, page, per_page):
    """
    Retorna uma fatia da lista `transacoes` de acordo com a paginação especificada.

    Args:
        transacoes (list): Lista de transações a serem paginadas.
        page (int): Número da página (deve ser maior que 0).
        per_page (int): Número de itens por página (deve ser maior que 0).

    Returns:
        list: Sublista contendo os itens da página solicitada.
    """
    # Garantir que transacoes é uma lista ou estrutura indexável
    if not isinstance(transacoes, (list, tuple)):
        raise ValueError("O parâmetro 'transacoes' deve ser uma lista ou tupla.")

    # Garantir que page e per_page são inteiros positivos
    if not isinstance(page, int) or not isinstance(per_page, int):
        raise ValueError("Os parâmetros 'page' e 'per_page' devem ser números inteiros.")
    if page < 1 or per_page < 1:
        return []  # Retorna lista vazia para entradas inválidas

    start = (page - 1) * per_page
    end = start + per_page

    # Evita erro de índice fora do limite
    return transacoes[start:end] if start < len(transacoes) else []


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
        if FIRST_DAY_OF_MONTH > LAST_DAY_OF_MONTH and today.day >= FIRST_DAY_OF_MONTH:
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
    transacoes_efetuada_all = paid_query.all()
    transacoes_efetuadas = convert_index_transactions(transacoes_efetuada_all)
    total_paid = len(transacoes_efetuadas)
    transacoes_efetuadas = make_pagination(transacoes_efetuadas, paid_page, paid_per_page)
    cards = db.query(Card).filter(Card.user_id == user.id).all()

    query_or = [
        and_(
            Transaction.card_id.is_(None),
            Transaction.due_day >= start_date,
            Transaction.due_day <= end_date,
        )
    ]
    for card in cards:
        if FIRST_DAY_OF_MONTH > LAST_DAY_OF_MONTH:
            if card.due_day < FIRST_DAY_OF_MONTH:
                year_card, month_card = shift_month(year, month, -1)
            else:
                year_card, month_card = shift_month(year, month, -2)
        else:
            if card.due_day < FIRST_DAY_OF_MONTH:
                year_card, month_card = year, month
            else:
                year_card, month_card = shift_month(year, month, -1)

        _, last_day = calendar.monthrange(year_card, month_card)
        open_invoice = card.close_day if card.close_day <= last_day else last_day
        invoice_start_date = date(year_card, month_card, open_invoice)

        if (card.close_day - 1) > 0:
            year_card_end, month_card_end = shift_month(year_card, month_card, 1)
            _, last_day = calendar.monthrange(year_card_end, month_card_end)
            close_invoice = (card.close_day - 1) if (card.close_day - 1) <= last_day else last_day
            invoice_end_date = date(year_card_end, month_card_end, close_invoice)
        else:
            invoice_end_date = date(year_card, month_card, last_day)
        query_or.append(
            and_(
                Transaction.card_id == card.id,
                Transaction.due_day >= invoice_start_date,
                Transaction.due_day <= invoice_end_date,
            )
        )
    # Transações Pendentes com paginação
    pending_query = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .filter(Transaction.paid_at.is_(None))
        .filter(or_(*query_or))
        .order_by(desc(Transaction.due_day))
    )

    transacoes_pendente_all = pending_query.all()
    transacoes_pendentes = convert_index_transactions(transacoes_pendente_all)
    total_pending = len(transacoes_pendentes)
    transacoes_pendentes = make_pagination(transacoes_pendentes, paid_page, paid_per_page)

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
    transaction.paid_at = datetime.now()
    db.commit()
    alert_success(request, "Transação marcada como paga!")
    return RedirectResponse(url="/", status_code=303)


@router.post("/cards/pay_invoice")
def pay_card_invoice(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    transaction_ids: str = Form(...),
):
    transaction_ids = [int(x) for x in transaction_ids.split(",")]
    transactions = (
        db.query(Transaction)
        .filter(Transaction.id.in_(transaction_ids), Transaction.user_id == user.id)
        .all()
    )
    paid_at = datetime.now()
    for t in transactions:
        t.paid_at = paid_at
    db.commit()
    alert_success(request, "Fatura paga com sucesso!")
    return RedirectResponse(url="/", status_code=303)
