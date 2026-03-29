"""Testes de integração para rotas de categorias (/categories)."""
from core.models import Category
from core.schemas import CategoryType


class TestGetCategories:
    def test_lista_categorias_retorna_200(self, client):
        response = client.get("/categories")
        assert response.status_code == 200

    def test_filtro_por_nome(self, client, test_category):
        response = client.get(f"/categories?f_name={test_category.name}")
        assert response.status_code == 200

    def test_filtro_por_tipo(self, client):
        response = client.get(f"/categories?f_type_filter={CategoryType.expense.value}")
        assert response.status_code == 200


class TestGetCategoryById:
    def test_retorna_json_da_categoria(self, client, test_category):
        response = client.get(f"/categories/{test_category.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_category.name

    def test_categoria_inexistente_retorna_404(self, client):
        response = client.get("/categories/999999")
        assert response.status_code == 404


class TestGetCategoryDetails:
    def test_retorna_detalhes_da_categoria(self, client, test_category):
        response = client.get(f"/categories/{test_category.id}/details")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_category.id
        assert "subcategories" in data
        assert "transactions" in data


class TestCreateCategory:
    def test_cria_categoria_redireciona(self, client):
        response = client.post(
            "/categories",
            data={
                "name": "Transporte",
                "type": CategoryType.expense.value,
                "icon": "fas fa-car",
                "color": "#0000ff",
                "parent_id": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/categories"

    def test_categoria_criada_persiste_no_banco(self, client, db, test_user):
        client.post(
            "/categories",
            data={
                "name": "Saúde",
                "type": CategoryType.expense.value,
                "icon": "fas fa-hospital",
                "color": "#00ff00",
                "parent_id": "",
            },
            follow_redirects=False,
        )
        cat = db.query(Category).filter(
            Category.user_id == test_user.id, Category.name == "Saúde"
        ).first()
        assert cat is not None
        assert cat.type == CategoryType.expense

    def test_cria_subcategoria_com_parent(self, client, db, test_user, test_category):
        client.post(
            "/categories",
            data={
                "name": "Restaurante",
                "type": CategoryType.expense.value,
                "icon": "fas fa-utensils",
                "color": "#ff5500",
                "parent_id": str(test_category.id),
            },
            follow_redirects=False,
        )
        sub = db.query(Category).filter(
            Category.user_id == test_user.id, Category.name == "Restaurante"
        ).first()
        assert sub is not None
        assert sub.parent_id == test_category.id


class TestEditCategory:
    def test_edita_categoria_redireciona(self, client, test_category):
        response = client.post(
            f"/categories/{test_category.id}/edit",
            data={
                "name": "Alimentação Editada",
                "type": CategoryType.expense.value,
                "icon": "fas fa-utensils",
                "color": "#123456",
                "parent_id": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_edicao_altera_dados_no_banco(self, client, db, test_category):
        client.post(
            f"/categories/{test_category.id}/edit",
            data={
                "name": "Comida",
                "type": CategoryType.income.value,
                "icon": "fas fa-apple-alt",
                "color": "#abcdef",
                "parent_id": "",
            },
            follow_redirects=False,
        )
        db.refresh(test_category)
        assert test_category.name == "Comida"
        assert test_category.type == CategoryType.income

    def test_nao_edita_categoria_do_sistema(self, client, db, test_user):
        sys_cat = Category(
            user_id=test_user.id,
            name="Sistema",
            type=CategoryType.expense,
            icon="fas fa-cog",
            color="#999",
            system_category=True,
        )
        db.add(sys_cat)
        db.commit()
        db.refresh(sys_cat)

        response = client.post(
            f"/categories/{sys_cat.id}/edit",
            data={
                "name": "Tentativa",
                "type": CategoryType.expense.value,
                "icon": "fas fa-cog",
                "color": "#999",
                "parent_id": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        db.refresh(sys_cat)
        assert sys_cat.name == "Sistema"  # não foi alterado


class TestDeleteCategory:
    def test_deleta_categoria_redireciona(self, client, test_category):
        response = client.post(
            f"/categories/{test_category.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_categoria_removida_do_banco(self, client, db, test_user):
        cat = Category(
            user_id=test_user.id,
            name="Temporária",
            type=CategoryType.expense,
            icon="fas fa-times",
            color="#000",
        )
        db.add(cat)
        db.commit()
        cat_id = cat.id

        client.post(f"/categories/{cat_id}/delete", follow_redirects=False)
        result = db.query(Category).filter(Category.id == cat_id).first()
        assert result is None

    def test_nao_deleta_categoria_do_sistema(self, client, db, test_user):
        sys_cat = Category(
            user_id=test_user.id,
            name="Ajuste",
            type=CategoryType.expense,
            icon="fas fa-cog",
            color="#555",
            system_category=True,
        )
        db.add(sys_cat)
        db.commit()
        sys_id = sys_cat.id

        client.post(f"/categories/{sys_id}/delete", follow_redirects=False)
        result = db.query(Category).filter(Category.id == sys_id).first()
        assert result is not None  # ainda existe
