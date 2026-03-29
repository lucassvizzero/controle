"""Rotas de configuração do usuário."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.auth import pwd_context
from core.database import get_db
from core.models import User, UserSettings
from core.templates import templates
from core.utils import alert_error, alert_success, get_alerts
from routes.auth import get_current_user

router = APIRouter()


def get_or_create_settings(db: Session, user_id: int) -> UserSettings:
    s = db.query(UserSettings).filter_by(user_id=user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("/settings")
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user_settings = get_or_create_settings(db, user.id)
    return templates.TemplateResponse(
        request,
        "pages/settings.html",
        {
            "request": request,
            "alerts": get_alerts(request),
            "user_settings": user_settings,
        },
    )


@router.post("/settings/period")
def update_period(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    period_start_day: int = Form(...),
    period_end_day: int = Form(...),
):
    if not (1 <= period_start_day <= 31) or not (1 <= period_end_day <= 31):
        alert_error(request, "Dias devem ser entre 1 e 31.")
        return RedirectResponse(url="/settings", status_code=303)
    if period_start_day == period_end_day:
        alert_error(request, "O dia de início e fim não podem ser iguais.")
        return RedirectResponse(url="/settings", status_code=303)

    s = get_or_create_settings(db, user.id)
    s.period_start_day = period_start_day
    s.period_end_day = period_end_day
    db.commit()

    alert_success(request, "Período de faturamento atualizado.")
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/settings/profile")
def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    name: str = Form(...),
    email: str = Form(...),
):
    existing = db.query(User).filter(User.email == email, User.id != user.id).first()
    if existing:
        alert_error(request, "Este e-mail já está em uso.")
        return RedirectResponse(url="/settings", status_code=303)

    user.name = name.strip()
    user.email = email.strip()
    db.commit()

    alert_success(request, "Perfil atualizado.")
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/settings/password")
def update_password(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    if not pwd_context.verify(current_password, user.password):
        alert_error(request, "Senha atual incorreta.")
        return RedirectResponse(url="/settings", status_code=303)
    if new_password != confirm_password:
        alert_error(request, "A nova senha e a confirmação não conferem.")
        return RedirectResponse(url="/settings", status_code=303)
    if len(new_password) < 6:
        alert_error(request, "A nova senha deve ter pelo menos 6 caracteres.")
        return RedirectResponse(url="/settings", status_code=303)

    user.password = pwd_context.hash(new_password)
    db.commit()

    alert_success(request, "Senha alterada com sucesso.")
    return RedirectResponse(url="/settings", status_code=303)
