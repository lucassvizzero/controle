"""Rotas de relatórios analíticos."""
import calendar
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from core.models import Account, Budget, Category, Transaction, UserSettings
from core.schemas import CategoryType
from core.templates import templates
from core.utils import get_alerts
from routes.auth import get_current_user
from routes.index import (
    FIRST_DAY_OF_MONTH,
    LAST_DAY_OF_MONTH,
    get_period_range,
    month_translation,
)

router = APIRouter(dependencies=[Depends(get_current_user)])

SHORT_MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _get_period_days(db: Session, user_id: int):
    cfg = db.query(UserSettings).filter_by(user_id=user_id).first()
    return (
        (cfg.period_start_day, cfg.period_end_day)
        if cfg else (FIRST_DAY_OF_MONTH, LAST_DAY_OF_MONTH)
    )


def _year_range(year: int):
    return datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59, 999999)


def _available_years(db: Session, user_id: int):
    rows = (
        db.query(func.extract("year", Transaction.paid_at).label("y"))
        .filter(Transaction.user_id == user_id, Transaction.paid_at.isnot(None), Transaction.is_deleted.is_(False))
        .distinct()
        .all()
    )
    years = sorted({int(r.y) for r in rows}, reverse=True)
    if not years:
        years = [date.today().year]
    return years


@router.get("/reports")
def reports_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Query(None),
):
    available_years = _available_years(db, user.id)
    if year is None:
        year = available_years[0] if available_years else date.today().year
    current_month = date.today().month
    return templates.TemplateResponse(
        request,
        "pages/reports.html",
        {
            "request": request,
            "alerts": get_alerts(request),
            "year": year,
            "current_month": current_month,
            "available_years": available_years,
        },
    )


@router.get("/reports/data/annual")
def data_annual(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Query(...),
):
    p_start, p_end = _get_period_days(db, user.id)
    entrou_list, saiu_list, investiu_list, sobrou_list = [], [], [], []

    for month in range(1, 13):
        start, end = get_period_range(year, month, p_start, p_end)
        txs = (
            db.query(Transaction)
            .options(joinedload(Transaction.category))
            .filter(
                Transaction.user_id == user.id,
                Transaction.paid_at >= start,
                Transaction.paid_at <= end,
                Transaction.is_deleted.is_(False),
            )
            .all()
        )
        entrou = sum(t.value for t in txs if t.category.type == CategoryType.income and t.card_id is None)
        saiu = sum(t.value for t in txs if t.category.type == CategoryType.expense)
        credito = sum(t.value for t in txs if t.category.type == CategoryType.income and t.card_id is not None)
        saiu = float(saiu) - float(credito)
        investiu = sum(t.value for t in txs if t.category.type == CategoryType.investment)

        entrou_list.append(round(float(entrou), 2))
        saiu_list.append(round(saiu, 2))
        investiu_list.append(round(float(investiu), 2))
        sobrou_list.append(round(float(entrou) - saiu - float(investiu), 2))

    return JSONResponse({
        "months": SHORT_MONTHS,
        "entrou": entrou_list,
        "saiu": saiu_list,
        "investiu": investiu_list,
        "sobrou": sobrou_list,
    })


@router.get("/reports/data/categories")
def data_categories(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Query(...),
    month: int = Query(0),
):
    p_start, p_end = _get_period_days(db, user.id)
    if month == 0:
        start, end = _year_range(year)
    else:
        start, end = get_period_range(year, month, p_start, p_end)

    txs = (
        db.query(Transaction)
        .options(joinedload(Transaction.category).joinedload(Category.parent))
        .filter(
            Transaction.user_id == user.id,
            Transaction.paid_at >= start,
            Transaction.paid_at <= end,
            Transaction.is_deleted.is_(False),
        )
        .all()
    )

    expense_totals: dict = {}
    income_totals: dict = {}

    for t in txs:
        cat = t.category
        root = cat if cat.parent_id is None else cat.parent
        if root is None:
            root = cat

        key = root.id
        if cat.type == CategoryType.expense:
            if key not in expense_totals:
                expense_totals[key] = {"name": root.name, "color": root.color or "#888", "icon": root.icon or "", "total": 0.0}
            expense_totals[key]["total"] += float(t.value)
        elif cat.type == CategoryType.income and t.card_id is None:
            if key not in income_totals:
                income_totals[key] = {"name": root.name, "color": root.color or "#888", "icon": root.icon or "", "total": 0.0}
            income_totals[key]["total"] += float(t.value)

    expense = sorted(expense_totals.values(), key=lambda x: x["total"], reverse=True)
    income = sorted(income_totals.values(), key=lambda x: x["total"], reverse=True)
    for item in expense + income:
        item["total"] = round(item["total"], 2)

    return JSONResponse({"expense": expense, "income": income})


@router.get("/reports/data/accounts")
def data_accounts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Query(...),
    month: int = Query(0),
):
    p_start, p_end = _get_period_days(db, user.id)
    if month == 0:
        start, end = _year_range(year)
    else:
        start, end = get_period_range(year, month, p_start, p_end)

    accounts = db.query(Account).filter_by(user_id=user.id).all()
    result = []
    for acc in accounts:
        txs = (
            db.query(Transaction)
            .options(joinedload(Transaction.category))
            .filter(
                Transaction.user_id == user.id,
                Transaction.account_id == acc.id,
                Transaction.paid_at >= start,
                Transaction.paid_at <= end,
                Transaction.is_deleted.is_(False),
            )
            .all()
        )
        income = sum(float(t.value) for t in txs if t.category.type == CategoryType.income and t.card_id is None)
        expense = sum(float(t.value) for t in txs if t.category.type == CategoryType.expense)
        if income > 0 or expense > 0:
            result.append({"name": acc.name, "income": round(income, 2), "expense": round(expense, 2)})

    return JSONResponse(result)


@router.get("/reports/data/budgets")
def data_budgets(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Query(...),
    month: int = Query(...),
):
    p_start, p_end = _get_period_days(db, user.id)
    start, end = get_period_range(year, month, p_start, p_end)
    month_date = date(year, month, 1)

    budgets = (
        db.query(Budget)
        .options(joinedload(Budget.category))
        .filter(Budget.user_id == user.id, Budget.month == month_date)
        .all()
    )

    result = []
    for b in budgets:
        spent_rows = (
            db.query(func.coalesce(func.sum(Transaction.value), 0))
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user.id,
                Transaction.paid_at >= start,
                Transaction.paid_at <= end,
                Transaction.is_deleted.is_(False),
                Category.type == CategoryType.expense,
                (Transaction.category_id == b.category_id) |
                (Category.parent_id == b.category_id),
            )
            .scalar()
        )
        spent = round(float(spent_rows or 0), 2)
        limit = round(float(b.limit_value), 2)
        percent = round((spent / limit * 100) if limit > 0 else 0, 1)
        result.append({
            "name": b.category.name,
            "color": b.category.color or "#888",
            "icon": b.category.icon or "",
            "limit": limit,
            "spent": spent,
            "percent": percent,
        })

    result.sort(key=lambda x: x["percent"], reverse=True)
    return JSONResponse(result)
