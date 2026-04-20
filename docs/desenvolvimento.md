# Guia de Desenvolvimento

## Setup Local

### Com Docker (recomendado)

```bash
# Copiar .env de exemplo
cp .env.example .env

# Subir containers
docker-compose up

# App: http://localhost:8000
# Postgres: localhost:5432
```

### Sem Docker

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql://admin:secret@localhost:5432/finance
export SECRET_KEY=dev-secret
uvicorn main:app --reload
```

---

## Como Adicionar um Novo CRUD

Exemplo: adicionar uma entidade "Tags".

### 1. Model (`core/models.py`)

```python
class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, default="#000000")
    user = relationship("User", back_populates="tags")
```

### 2. Route (`routes/tags.py`)

Seguir o pattern de `routes/accounts.py`:

```python
router = APIRouter(prefix="/tags", dependencies=[Depends(get_current_user)])

@router.get("/")
def get_tags(request, db, user, page, per_page, sort_by, sort_order):
    # Query
    # Montar columns, values, crud_schema, filter_schema
    # Retornar TemplateResponse com TemplateContext
    pass

@router.post("/")
def create_tag(request, db, user, name, color):
    pass

# ... edit, delete
```

### 3. Template (`templates/pages/tags.html`)

```html
{% extends "base.html" %}
{% block title %}Tags{% endblock %}
{% block header %}Tags{% endblock %}
{% block content %}
  {% include "components/alerts.html" %}
  {% include "components/datagrid.html" %}
  {% include "components/crud_modal.html" %}
{% endblock %}
```

### 4. Registrar no `main.py`

```python
from routes import tags
app.include_router(tags.router)
```

### 5. Sidebar (`templates/components/sidebar.html`)

Adicionar link na navegacao.

---

## Schemas do CRUD Generico

### Column (tabela)

```python
Column(label="Nome", key="name", type="text", sortable=True)
Column(label="Cor", key="color", type="color")
```

### CrudField (formulario)

```python
CrudField(name="name", label="Nome", type="text", required=True)
CrudField(name="color", label="Cor", type="color", required=False)
CrudField(name="account_id", label="Conta", type="combobox", options=[...])
CrudField(name="is_active", label="Ativo", type="switch")
CrudField(name="value", label="Valor", type="currency", min=0, step=0.01)
```

Tipos suportados: `text`, `number`, `date`, `datetime-local`, `combobox`, `switch`, `color`, `icon`, `currency`, `hidden`.

### FilterField (filtros)

```python
FilterField(name="f_name", label="Nome", type="text")
FilterField(name="f_bank", label="Banco", type="combobox", options=[...])
```

### Permissions

```python
Permissions(add=True, edit=True, delete=True, detail=False, upload=False, filter=True)
```

---

## Soft Delete

Transacoes usam soft delete via `is_deleted=True`. Todas as queries filtram `is_deleted.is_(False)`.

Para deletar: `POST /transactions/{id}/delete` seta `is_deleted=True`.
Para restaurar: `POST /transactions/{id}/undodelete` seta `is_deleted=False`.

---

## Transacoes Recorrentes

Ao criar transacao com `is_recurring=True`:
1. Cria a transacao pai
2. Gera transacoes filhas com `parent_id` apontando para o pai
3. Frequencias: semanal, mensal, bimestral, trimestral, semestral, anual
4. Respeita `recurring_end_date` se definido

Parcelas: `installments > 1` gera N transacoes com `current_installment` incrementando.

---

## Flash Messages

```python
from core.utils import alert_success, alert_error, alert_info

alert_success(request, "Operacao realizada!")
alert_error(request, "Algo deu errado.")
```

Sao armazenadas na sessao e consumidas pelo template `components/alerts.html`.

---

## Filtros Jinja2 Customizados

Definidos em `core/templates.py`:

- `strftime`: `{{ date_obj|strftime('%d/%m/%Y') }}`
- `currency`: `{{ value|currency }}` -> "R$ 1.234,56"

---

## Variaveis de Ambiente

| Variavel | Descricao | Default |
|----------|-----------|---------|
| `DATABASE_URL` | Connection string PostgreSQL | - |
| `SECRET_KEY` | Chave para JWT | dev value |
| `ALGORITHM` | Algoritmo JWT | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiracao do token | 360 |
| `ENVIRONMENT` | development / production | development |

---

## Dicas para Desenvolvimento

1. **Hot reload**: Com Docker, o volume mount faz hot reload funcionar automaticamente
2. **Logs**: `docker logs finance_api -f` para acompanhar
3. **DB direto**: `docker exec finance_db psql -U admin -d finance` para queries manuais
4. **Rebuild**: `docker-compose up --build` apos mudar requirements.txt
5. **Migrations**: Usar Alembic (`alembic revision --autogenerate -m "descricao"`, `alembic upgrade head`)
6. **Fixtures**: Rodam automaticamente no startup. Para dados de dev, descomentar `fixtures_dev()` em `core/fixtures.py`
