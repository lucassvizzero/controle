"""Testes de integração para rotas da dashboard (/index)."""
from datetime import date

from core.models import Category, Transaction
from core.schemas import CategoryType


def _make_system_category(db, user, name, cat_type):
    cat = Category(
        user_id=user.id,
        name=name,
        type=cat_type,
        icon="fas fa-circle",
        color="#888",
        system_category=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


class TestDashboard:
    def test_dashboard_retorna_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_dashboard_com_mes_especifico(self, client):
        response = client.get("/?year=2026&month=3")
        assert response.status_code == 200

    def test_dashboard_preview(self, client):
        response = client.get("/?preview=true")
        assert response.status_code == 200


class TestRegistryPayment:
    def test_marcar_pago_atualiza_paid_at(self, client, db, test_transaction):
        response = client.post(
            "/registry_payment",
            json={
                "transaction_id": str(test_transaction.id),
                "description": test_transaction.description,
                "payment_date": "2026-03-15T00:00:00",
                "value": float(test_transaction.value),
            },
        )
        assert response.status_code in (200, 303, 307)
        db.refresh(test_transaction)
        assert test_transaction.paid_at is not None

    def test_transacao_inexistente_redireciona(self, client):
        response = client.post(
            "/registry_payment",
            json={
                "transaction_id": "999999",
                "description": "X",
                "payment_date": "2026-03-15T00:00:00",
                "value": 1.0,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestUndoPayment:
    def test_desfazer_pagamento_zera_paid_at(self, client, db, test_user, test_account, test_category):
        tx = Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            description="Pago",
            value=100.0,
            due_at=date(2026, 3, 10),
            paid_at=date(2026, 3, 10),
            is_deleted=False,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        response = client.post(
            "/undo-payment",
            json={"transaction_id": str(tx.id)},
        )
        assert response.status_code in (200, 303, 307)
        db.refresh(tx)
        assert tx.paid_at is None

    def test_desfazer_fatura_multiplas_transacoes(self, client, db, test_user, test_account, test_category):
        tx1 = Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            description="Item 1",
            value=50.0,
            due_at=date(2026, 3, 5),
            paid_at=date(2026, 3, 10),
            is_deleted=False,
        )
        tx2 = Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            description="Item 2",
            value=75.0,
            due_at=date(2026, 3, 5),
            paid_at=date(2026, 3, 10),
            is_deleted=False,
        )
        db.add_all([tx1, tx2])
        db.commit()
        db.refresh(tx1)
        db.refresh(tx2)

        client.post(
            "/undo-payment",
            json={"transaction_id": f"{tx1.id},{tx2.id}"},
        )
        db.refresh(tx1)
        db.refresh(tx2)
        assert tx1.paid_at is None
        assert tx2.paid_at is None

    def test_transacao_inexistente_redireciona(self, client):
        response = client.post(
            "/undo-payment",
            json={"transaction_id": "999999"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_nao_desfaz_transacao_de_outro_usuario(self, client, db, test_account, test_category):
        from core.auth import pwd_context
        from core.models import User

        outro = User(
            name="Outro",
            email="outro2@exemplo.com",
            username="outro2",
            password=pwd_context.hash("senha"),
        )
        db.add(outro)
        db.commit()
        db.refresh(outro)

        tx = Transaction(
            user_id=outro.id,
            account_id=test_account.id,
            category_id=test_category.id,
            description="Pago outro",
            value=99.0,
            due_at=date(2026, 3, 1),
            paid_at=date(2026, 3, 1),
            is_deleted=False,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        client.post("/undo-payment", json={"transaction_id": str(tx.id)})
        db.refresh(tx)
        # paid_at não deve ter sido alterado — transação pertence a outro usuário
        assert tx.paid_at is not None


class TestAjusteSobrou:
    def test_ajuste_positivo_cria_outras_entradas(self, client, db, test_user, test_account):
        cat_entradas = _make_system_category(db, test_user, "Outras Entradas", CategoryType.income)

        response = client.post(
            "/adjust-sobrou",
            data={
                "sobrou_atual": "100.00",
                "novo_sobrou": "150.00",
                "year": "2026",
                "month": "3",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        tx = db.query(Transaction).filter(
            Transaction.user_id == test_user.id,
            Transaction.category_id == cat_entradas.id,
            Transaction.description == "Ajuste Sobrou",
        ).first()
        assert tx is not None
        assert float(tx.value) == 50.0
        assert tx.paid_at is not None

    def test_ajuste_negativo_cria_outras_saidas(self, client, db, test_user, test_account):
        cat_saidas = _make_system_category(db, test_user, "Outras Saídas", CategoryType.expense)

        response = client.post(
            "/adjust-sobrou",
            data={
                "sobrou_atual": "200.00",
                "novo_sobrou": "120.00",
                "year": "2026",
                "month": "3",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        tx = db.query(Transaction).filter(
            Transaction.user_id == test_user.id,
            Transaction.category_id == cat_saidas.id,
            Transaction.description == "Ajuste Sobrou",
        ).first()
        assert tx is not None
        assert float(tx.value) == 80.0

    def test_ajuste_zero_nao_cria_transacao(self, client, db, test_user):
        count_antes = db.query(Transaction).filter(
            Transaction.user_id == test_user.id,
            Transaction.description == "Ajuste Sobrou",
        ).count()

        client.post(
            "/adjust-sobrou",
            data={
                "sobrou_atual": "100.00",
                "novo_sobrou": "100.00",
                "year": "2026",
                "month": "3",
            },
            follow_redirects=False,
        )

        count_depois = db.query(Transaction).filter(
            Transaction.user_id == test_user.id,
            Transaction.description == "Ajuste Sobrou",
        ).count()
        assert count_depois == count_antes

    def test_sem_categoria_redireciona_sem_criar(self, client, db, test_user):
        """Sem a categoria de sistema, o endpoint redireciona com erro sem criar transação."""
        count_antes = db.query(Transaction).filter(Transaction.user_id == test_user.id).count()

        client.post(
            "/adjust-sobrou",
            data={
                "sobrou_atual": "50.00",
                "novo_sobrou": "200.00",
                "year": "2026",
                "month": "3",
            },
            follow_redirects=False,
        )

        count_depois = db.query(Transaction).filter(Transaction.user_id == test_user.id).count()
        assert count_depois == count_antes
