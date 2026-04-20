# Arquitetura do Sistema

## Stack

- **Backend:** FastAPI + SQLAlchemy ORM + PostgreSQL
- **Frontend:** Jinja2 (server-side rendering) + Tailwind CSS + DaisyUI
- **Auth:** JWT em cookie httponly (python-jose + passlib/bcrypt)
- **Infra:** Docker Compose (app + postgres:15-alpine)

Sem build step de frontend. Todo o HTML e gerado no servidor.

---

## Fluxo de uma Request

```
Browser -> FastAPI (main.py)
            |
            ├─ Middleware: SessionMiddleware (cookie de sessao)
            ├�� Middleware: RedirectUnauthorizedMiddleware (401 -> /login)
            ├─ Middleware: CORS
            |
            └─ Router (routes/*.py)
                  |
                  ├─ Dependency: get_current_user() -> valida JWT do cookie
                  ├─ Dependency: get_db() -> abre sessao SQLAlchemy
                  |
                  └─ Handler
                        ├─ Query no banco via SQLAlchemy
                        ├─ Monta contexto (TemplateContext ou dict)
                        └─ Retorna TemplateResponse (Jinja2)
```

---

## Estrutura de Diretórios

```
controle/
├── main.py                 # Inicializacao do app, middlewares, routers
├── core/
│   ├── models.py           # Modelos SQLAlchemy (User, Account, Card, Category, Budget, Transaction, MonthlyBalance, MonthlySavings)
│   ├── schemas.py          # Pydantic: validacao, enums, schemas do CRUD generico
│   ├── database.py         # Engine, SessionLocal, Base, get_db()
│   ��── settings.py         # Variaveis de ambiente (SECRET_KEY, DATABASE_URL, etc)
│   ├── auth.py             # JWT encode/decode, bcrypt context
│   ├── balance.py          # Calculo de saldo mensal e total guardado
│   ├── fixtures.py         # Seed data (categorias padrao por usuario)
│   ├── templates.py        # Jinja2 env + filtros customizados (strftime, currency)
│   └── utils.py            # Flash messages (alert_success, alert_error, etc)
├── routes/
│   ├── auth.py             # Dependency get_current_user()
│   ├── login.py            # GET/POST /login, /logout
│   ├── register.py         # GET/POST /register
│   ├── index.py            # Dashboard (GET /) - ~700 linhas, mais complexo
│   ├── transactions.py     # CRUD transacoes + Excel import/export - ~1400 linhas
│   ├── accounts.py         # CRUD contas
│   ├── cards.py            # CRUD cartoes
│   ├── categories.py       # CRUD categorias (com subcategorias)
│   ├── budgets.py          # CRUD orcamentos
│   ├── settings.py         # Configuracoes do usuario (periodo, perfil, senha)
│   ├── reports.py          # Relatorios analiticos (JSON endpoints + pagina)
│   └── balance.py          # Edicao manual de saldo/guardado
├── templates/
│   ├── base.html           # Layout principal (sidebar, navbar)
│   ├── base_auth.html      # Layout de auth (login/register)
│   ├── pages/              # Paginas (index, transactions, accounts, etc)
│   └── components/         # Componentes reutilizaveis (datagrid, crud_modal, etc)
├── static/                 # Logo, favicon
├── alembic/                # Migrations (Alembic)
├── tests/                  # Testes
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Banco de Dados - Modelos

### Diagrama de Relacionamento

```
User (1)
 ├── (N) Account
 │        └── (N) Card
 ��── (N) Category (self-ref: parent_id)
 ├── (N) Budget
 ├── (N) Transaction
 │        ├── FK -> Account
 │        ├── FK -> Category
 │        ├── FK -> Card (opcional)
 │        └── FK -> Transaction (parent_id, para recorrentes)
 ├── (1) UserSettings
 ├── (N) MonthlyBalance
 └── (N) MonthlySavings
```

### Campos Importantes

**Transaction** (tabela mais complexa):
- `value`: DECIMAL(15,2)
- `due_at`: Date (vencimento)
- `paid_at`: DateTime nullable (NULL = pendente)
- `is_deleted`: Boolean (soft delete)
- `is_recurring` + `recurring_frequency`: Transacoes recorrentes
- `installments` + `current_installment`: Parcelas
- `parent_id`: Liga filhos ao pai recorrente
- `card_id`: Se preenchido, a transacao pertence a uma fatura de cartao

**Category**:
- `type`: income | expense | transfer | invoice | investment
- `parent_id`: Subcategorias (self-referential)
- `system_category`: Categorias do sistema (nao editaveis pelo usuario)

**MonthlyBalance / MonthlySavings**:
- Campos `*_manual`: Quando true, o valor foi definido manualmente e nao e recalculado
- Propagacao: Alterar um mes propaga saldo_final para o saldo_inicial do proximo

---

## Autenticacao

1. **Login**: POST /login -> valida senha (bcrypt) -> gera JWT -> seta cookie `session_token` (httponly, secure em prod)
2. **Request autenticada**: `get_current_user()` le o cookie, decodifica JWT, busca User no banco
3. **401**: O `RedirectUnauthorizedMiddleware` intercepta e redireciona para /login
4. **Logout**: POST /logout -> remove cookie

Token expira em 360 minutos (configuravel via `ACCESS_TOKEN_EXPIRE_MINUTES`).

---

## Periodo de Faturamento (Billing Period)

O dashboard usa um periodo customizavel (padrao: dia 20 do mes anterior ate dia 19 do mes atual).

- Configurado em `UserSettings.period_start_day` e `period_end_day`
- Quando `period_start_day > period_end_day`, o periodo cruza meses
- Exemplo: periodo 20-19 para "Maio" = 20/Abr a 19/Mai

Funcoes chave:
- `get_period_range(year, month, first_day, last_day)` -> retorna (start_date, end_date)
- `shift_month(year, month, delta)` -> avanca/retrocede meses

---

## Logica de Faturas de Cartao

As transacoes de cartao sao agrupadas em "faturas" virtuais pelo `convert_index_transactions()`:

1. Busca transacoes do cartao no periodo da fatura (baseado em `close_day`)
2. Agrupa por cartao e mes de fechamento
3. Transacoes com `due_at.day >= close_day` sao atribuidas ao mes seguinte
4. Cria um `TransactionIndexOut` com `is_card_invoice=True` que contem a lista de transacoes

A query do dashboard calcula o range de datas para cada cartao baseado no `due_day` e `close_day`.

---

## Pattern: CRUD Genérico

Os CRUDs (accounts, cards, categories, budgets, transactions) seguem um pattern:

1. **Route**: Monta `TemplateContext` com:
   - `columns`: Lista de `Column` (label, tipo, se e sortable)
   - `values`: Lista de listas (linhas da tabela)
   - `crud_schema`: Lista de `CrudField` (campos do formulario add/edit)
   - `filter_schema`: Lista de `FilterField` (filtros)
   - `permissions`: `Permissions(add=True, edit=True, ...)`

2. **Template**: Inclui componentes genéricos:
   - `datagrid.html`: Renderiza tabela com sort e paginacao
   - `crud_modal.html`: Modal com formulario dinâmico
   - `detail_modal.html`: Modal de detalhes

Tipos de campo suportados: text, number, date, datetime-local, combobox, switch, color, icon, currency.

---

## Saldo Mensal e Total Guardado

Calculados automaticamente no dashboard (`recalculate_balance`, `recalculate_savings`):

```
saldo_inicial = saldo_final do mes anterior (se nao manual)
saldo_final = saldo_inicial + entrou - saiu - investiu (se nao manual)

total_guardado = total_guardado do mes anterior + investiu (se nao manual)
```

Endpoints em `routes/balance.py` permitem edicao manual (seta flag `*_manual=True`).
Ao resetar, recalcula automaticamente e propaga para meses futuros.
