"""Testes unitários para core/auth.py."""
from datetime import timedelta

import pytest
from jose import jwt

from core.auth import create_access_token, pwd_context
from core.settings import ALGORITHM, SECRET_KEY


class TestPasswordHashing:
    def test_hash_returns_different_string(self):
        hashed = pwd_context.hash("senha123")
        assert hashed != "senha123"

    def test_verify_correct_password(self):
        hashed = pwd_context.hash("senha123")
        assert pwd_context.verify("senha123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = pwd_context.hash("senha123")
        assert pwd_context.verify("errada", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """Bcrypt usa salt aleatório — dois hashes da mesma senha são diferentes."""
        h1 = pwd_context.hash("senha123")
        h2 = pwd_context.hash("senha123")
        assert h1 != h2

    def test_empty_password_hashes(self):
        hashed = pwd_context.hash("")
        assert pwd_context.verify("", hashed) is True


class TestCreateAccessToken:
    def test_token_contains_sub(self):
        token = create_access_token(data={"sub": "user@test.com"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user@test.com"

    def test_token_contains_exp(self):
        token = create_access_token(data={"sub": "user@test.com"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry_respected(self):
        from datetime import datetime
        delta = timedelta(minutes=5)
        before = datetime.utcnow()
        token = create_access_token(data={"sub": "user@test.com"}, expires_delta=delta)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.utcfromtimestamp(payload["exp"])
        # Expiração deve ser aproximadamente now + 5 minutos
        diff = (exp - before).total_seconds()
        assert 290 <= diff <= 310  # 5 min ± margem

    def test_invalid_key_raises(self):
        from jose import JWTError
        token = create_access_token(data={"sub": "user@test.com"})
        with pytest.raises(JWTError):
            jwt.decode(token, "chave_errada", algorithms=[ALGORITHM])

    def test_extra_claims_preserved(self):
        token = create_access_token(data={"sub": "user@test.com", "role": "admin"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["role"] == "admin"
