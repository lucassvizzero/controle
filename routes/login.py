from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.auth import create_access_token, pwd_context
from core.database import get_db
from core.models import User
from core.settings import ACCESS_TOKEN_EXPIRE_MINUTES, ENVIRONMENT
from core.templates import templates

router = APIRouter()


@router.get("/login")
def get_login(request: Request):
    """Rota para exibir o formulário de login."""
    return templates.TemplateResponse(request, "pages/login.html", {"error": None})


@router.post("/login")
def post_login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    """Processa o login do usuário."""
    user = db.query(User).filter(User.username == username).first()

    if not user or not pwd_context.verify(password, user.password):
        return templates.TemplateResponse(
            request, "pages/login.html", {"error": "Usuário ou senha inválidos"}
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        secure=ENVIRONMENT == "production",
        samesite="Lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return response
