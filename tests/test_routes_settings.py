"""Testes de integração para rotas de configurações (/settings)."""
from core.models import UserSettings


class TestSettingsPage:
    def test_pagina_retorna_200(self, client):
        response = client.get("/settings")
        assert response.status_code == 200

    def test_cria_settings_padrao_se_nao_existir(self, client, db, test_user):
        client.get("/settings")
        s = db.query(UserSettings).filter_by(user_id=test_user.id).first()
        assert s is not None
        assert s.period_start_day == 20
        assert s.period_end_day == 19


class TestUpdatePeriod:
    def test_atualiza_periodo_redireciona(self, client):
        response = client.post(
            "/settings/period",
            data={"period_start_day": "1", "period_end_day": "31"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/settings"

    def test_periodo_persiste_no_banco(self, client, db, test_user):
        client.post(
            "/settings/period",
            data={"period_start_day": "15", "period_end_day": "14"},
            follow_redirects=False,
        )
        s = db.query(UserSettings).filter_by(user_id=test_user.id).first()
        assert s is not None
        assert s.period_start_day == 15
        assert s.period_end_day == 14

    def test_dia_invalido_redireciona_sem_alterar(self, client, db, test_user):
        # Cria settings com valores conhecidos
        s = UserSettings(user_id=test_user.id, period_start_day=20, period_end_day=19)
        db.add(s)
        db.commit()

        client.post(
            "/settings/period",
            data={"period_start_day": "0", "period_end_day": "19"},
            follow_redirects=False,
        )
        db.refresh(s)
        assert s.period_start_day == 20  # não alterou

    def test_inicio_igual_fim_invalido(self, client, db, test_user):
        s = UserSettings(user_id=test_user.id, period_start_day=20, period_end_day=19)
        db.add(s)
        db.commit()

        client.post(
            "/settings/period",
            data={"period_start_day": "10", "period_end_day": "10"},
            follow_redirects=False,
        )
        db.refresh(s)
        assert s.period_start_day == 20  # não alterou


class TestUpdateProfile:
    def test_atualiza_nome_email(self, client, db, test_user):
        client.post(
            "/settings/profile",
            data={"name": "Novo Nome", "email": "novo@exemplo.com"},
            follow_redirects=False,
        )
        db.refresh(test_user)
        assert test_user.name == "Novo Nome"
        assert test_user.email == "novo@exemplo.com"

    def test_email_duplicado_nao_altera(self, client, db, test_user):
        from core.auth import pwd_context
        from core.models import User

        outro = User(
            name="Outro",
            email="ocupado@exemplo.com",
            username="outro_settings",
            password=pwd_context.hash("senha"),
        )
        db.add(outro)
        db.commit()

        original_email = test_user.email
        client.post(
            "/settings/profile",
            data={"name": "Qualquer", "email": "ocupado@exemplo.com"},
            follow_redirects=False,
        )
        db.refresh(test_user)
        assert test_user.email == original_email


class TestUpdatePassword:
    def test_senha_correta_altera(self, client, db, test_user):
        from core.auth import pwd_context

        response = client.post(
            "/settings/password",
            data={
                "current_password": "senha123",
                "new_password": "novasenha",
                "confirm_password": "novasenha",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        db.refresh(test_user)
        assert pwd_context.verify("novasenha", test_user.password)

    def test_senha_atual_incorreta_nao_altera(self, client, db, test_user):
        from core.auth import pwd_context

        original_hash = test_user.password
        client.post(
            "/settings/password",
            data={
                "current_password": "errada",
                "new_password": "novasenha",
                "confirm_password": "novasenha",
            },
            follow_redirects=False,
        )
        db.refresh(test_user)
        assert test_user.password == original_hash

    def test_confirmacao_diferente_nao_altera(self, client, db, test_user):
        original_hash = test_user.password
        client.post(
            "/settings/password",
            data={
                "current_password": "senha123",
                "new_password": "novasenha",
                "confirm_password": "outracoisa",
            },
            follow_redirects=False,
        )
        db.refresh(test_user)
        assert test_user.password == original_hash

    def test_senha_curta_nao_altera(self, client, db, test_user):
        original_hash = test_user.password
        client.post(
            "/settings/password",
            data={
                "current_password": "senha123",
                "new_password": "abc",
                "confirm_password": "abc",
            },
            follow_redirects=False,
        )
        db.refresh(test_user)
        assert test_user.password == original_hash
