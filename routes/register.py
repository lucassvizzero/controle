from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import User
from core.templates import templates

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/register")
def get_register(request: Request):
    """Rota para exibir o formulário de cadastro."""
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


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
            "register.html", {"request": request, "error": "E-mail já cadastrado"}
        )

    hashed_password = pwd_context.hash(password)
    new_user = User(name=name, email=email, password=hashed_password)
    db.add(new_user)
    db.commit()

    return RedirectResponse(url="/login", status_code=303)
