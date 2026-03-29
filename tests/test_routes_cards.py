"""Testes de integração para rotas de cartões (/cards)."""
from core.models import Card
from core.schemas import BrandName


class TestGetCards:
    def test_lista_cartoes_retorna_200(self, client):
        response = client.get("/cards")
        assert response.status_code == 200

    def test_filtro_por_nome(self, client, test_card):
        response = client.get(f"/cards?f_name={test_card.name}")
        assert response.status_code == 200

    def test_filtro_por_bandeira(self, client, test_card):
        response = client.get(f"/cards?f_brand={test_card.brand.value}")
        assert response.status_code == 200


class TestGetCardById:
    def test_retorna_json_do_cartao(self, client, test_card):
        response = client.get(f"/cards/{test_card.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_card.name
        assert data["due_day"] == test_card.due_day

    def test_cartao_inexistente_retorna_404(self, client):
        response = client.get("/cards/999999")
        assert response.status_code == 404


class TestCreateCard:
    def test_cria_cartao_redireciona(self, client, test_account):
        response = client.post(
            "/cards",
            data={
                "account_id": test_account.id,
                "name": "Novo Cartão",
                "brand": BrandName.mastercard.value,
                "due_day": "15",
                "close_day": "8",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/cards"

    def test_cartao_criado_persiste_no_banco(self, client, db, test_user, test_account):
        client.post(
            "/cards",
            data={
                "account_id": test_account.id,
                "name": "Visa Gold",
                "brand": BrandName.visa.value,
                "due_day": "5",
                "close_day": "28",
            },
            follow_redirects=False,
        )
        card = db.query(Card).filter(
            Card.user_id == test_user.id, Card.name == "Visa Gold"
        ).first()
        assert card is not None
        assert card.due_day == 5
        assert card.brand == BrandName.visa


class TestEditCard:
    def test_edita_cartao_redireciona(self, client, test_card, test_account):
        response = client.post(
            f"/cards/{test_card.id}/edit",
            data={
                "account_id": test_account.id,
                "name": "Cartão Editado",
                "brand": BrandName.american_express.value,
                "due_day": "20",
                "close_day": "13",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_edicao_altera_dados_no_banco(self, client, db, test_card, test_account):
        client.post(
            f"/cards/{test_card.id}/edit",
            data={
                "account_id": test_account.id,
                "name": "Amex Platinum",
                "brand": BrandName.american_express.value,
                "due_day": "25",
                "close_day": "18",
            },
            follow_redirects=False,
        )
        db.refresh(test_card)
        assert test_card.name == "Amex Platinum"
        assert test_card.due_day == 25


class TestDeleteCard:
    def test_deleta_cartao_redireciona(self, client, test_card):
        response = client.post(
            f"/cards/{test_card.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_cartao_removido_do_banco(self, client, db, test_card):
        card_id = test_card.id
        client.post(f"/cards/{card_id}/delete", follow_redirects=False)
        card = db.query(Card).filter(Card.id == card_id).first()
        assert card is None

    def test_deletar_inexistente_nao_falha(self, client):
        response = client.post("/cards/999999/delete", follow_redirects=False)
        assert response.status_code == 303
