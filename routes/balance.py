"""Rotas para edição manual de Saldo em Conta e Total Guardado."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.balance import (
    get_or_create_balance,
    get_or_create_savings,
    propagate_balances_forward,
    propagate_savings_forward,
)
from core.database import get_db
from core.utils import alert_error, alert_success
from routes.auth import get_current_user

router = APIRouter(prefix="/balance", dependencies=[Depends(get_current_user)])


@router.post("/saldo-inicial")
def update_saldo_inicial(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Form(...),
    month: int = Form(...),
    value: float = Form(...),
):
    balance = get_or_create_balance(db, user.id, year, month)
    balance.saldo_inicial = Decimal(str(value))
    balance.saldo_inicial_manual = True

    # Recalcular saldo_final se não for manual
    if not balance.saldo_final_manual:
        # saldo_final será recalculado no próximo acesso ao dashboard
        # pois depende das transações do período
        pass

    db.commit()
    propagate_balances_forward(db, user.id, year, month)
    db.commit()

    alert_success(request, f"Saldo inicial atualizado para R$ {value:.2f}")
    return RedirectResponse(url=f"/?year={year}&month={month}", status_code=303)


@router.post("/saldo-final")
def update_saldo_final(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Form(...),
    month: int = Form(...),
    value: float = Form(...),
):
    balance = get_or_create_balance(db, user.id, year, month)
    balance.saldo_final = Decimal(str(value))
    balance.saldo_final_manual = True
    db.commit()

    propagate_balances_forward(db, user.id, year, month)
    db.commit()

    alert_success(request, f"Saldo final atualizado para R$ {value:.2f}")
    return RedirectResponse(url=f"/?year={year}&month={month}", status_code=303)


@router.post("/total-guardado")
def update_total_guardado(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Form(...),
    month: int = Form(...),
    value: float = Form(...),
):
    savings = get_or_create_savings(db, user.id, year, month)
    savings.total_guardado = Decimal(str(value))
    savings.is_manual = True
    db.commit()

    propagate_savings_forward(db, user.id, year, month)
    db.commit()

    alert_success(request, f"Total guardado atualizado para R$ {value:.2f}")
    return RedirectResponse(url=f"/?year={year}&month={month}", status_code=303)


@router.post("/reset")
def reset_balance(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    year: int = Form(...),
    month: int = Form(...),
    field: str = Form(...),
):
    """Remove flag manual de um campo, permitindo recálculo automático."""
    if field in ("saldo_inicial", "saldo_final"):
        balance = get_or_create_balance(db, user.id, year, month)
        if field == "saldo_inicial":
            balance.saldo_inicial_manual = False
        else:
            balance.saldo_final_manual = False
        db.commit()
    elif field == "total_guardado":
        savings = get_or_create_savings(db, user.id, year, month)
        savings.is_manual = False
        db.commit()
    else:
        alert_error(request, "Campo inválido.")
        return RedirectResponse(url=f"/?year={year}&month={month}", status_code=303)

    alert_success(request, "Valor será recalculado automaticamente.")
    return RedirectResponse(url=f"/?year={year}&month={month}", status_code=303)
