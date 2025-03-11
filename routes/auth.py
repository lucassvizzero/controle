from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.templating import Jinja2Templates
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import User
from core.settings import ALGORITHM, SECRET_KEY

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


from fastapi import Cookie, Depends, HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import User
from core.settings import ALGORITHM, SECRET_KEY


def get_current_user(
    request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)
):
    """Obtém o usuário autenticado pelo token no cookie de sessão. Se falhar, levanta um erro 401."""
    if hasattr(request.state, "user"):
        return request.state.user

    if not session_token:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")

    try:
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")

        if not user_email:
            raise HTTPException(status_code=401, detail="Token inválido")

        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        request.state.user = user
        print("setting user in request.state")
        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
