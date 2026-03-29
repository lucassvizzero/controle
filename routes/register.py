from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import EmailStr
from sqlalchemy.orm import Session

from core.auth import pwd_context
from core.database import get_db
from core.models import User
from core.templates import templates

router = APIRouter()


@router.get("/register")
def get_register(request: Request):
    """Rota para exibir o formulário de cadastro."""
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register")
def post_register(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
):
    """Processa o cadastro do usuário."""
    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        return templates.TemplateResponse(
            request, "register.html", {"error": "E-mail já cadastrado"}
        )

    hashed_password = pwd_context.hash(password)
    new_user = User(name=name, email=email, password=hashed_password)
    db.add(new_user)
    db.commit()

    return RedirectResponse(url="/login", status_code=303)
