# Endpoints da API

## Autenticacao

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/login` | Pagina de login |
| POST | `/login` | Autentica usuario (username + password) -> seta cookie JWT |
| POST | `/logout` | Remove cookie de sessao |
| GET | `/register` | Pagina de registro |
| POST | `/register` | Cria novo usuario |

---

## Dashboard

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/` | Dashboard principal. Query params: `year`, `month`, `paid_page`, `paid_per_page`, `pending_page`, `pending_per_page`, `preview` |
| POST | `/registry_payment` | Marca transacao/fatura como paga (Body: transaction_id, description, payment_date, value) |
| POST | `/undo-payment` | Desfaz pagamento (Body: transaction_id) |
| POST | `/adjust-sobrou` | Cria transacao de ajuste para corrigir o "sobrou" (Form: novo_sobrou, sobrou_atual, year, month) |

---

## Transacoes

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/transactions` | Lista com filtros: f_description, f_situation (1=pago, 2=pendente), f_account_id, f_card_id, f_category_id, f_category_type, f_transaction_type, f_due_at_start/end, f_paid_at_start/end |
| GET | `/transactions/{id}` | Detalhe da transacao (JSON) |
| POST | `/transactions` | Cria transacao. Se `is_recurring=True`, gera filhos automaticamente |
| POST | `/transactions/{id}/edit` | Edita transacao |
| POST | `/transactions/{id}/delete` | Soft delete (is_deleted=True) |
| POST | `/transactions/{id}/undodelete` | Restaura transacao deletada |
| GET | `/transactions/export` | Exporta Excel (.xlsx) |
| POST | `/transactions/import` | Importa Excel |

---

## Contas

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/accounts` | Lista com filtros (f_name, f_bank) e sort |
| GET | `/accounts/{id}` | Detalhe (JSON) |
| POST | `/accounts` | Cria conta |
| POST | `/accounts/{id}/edit` | Edita |
| POST | `/accounts/{id}/delete` | Deleta (cascade em cards e transacoes) |

---

## Cartoes

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/cards` | Lista com filtros (f_account_id, f_name, f_brand) e sort |
| POST | `/cards` | Cria cartao |
| POST | `/cards/{id}/edit` | Edita |
| POST | `/cards/{id}/delete` | Deleta |

---

## Categorias

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/categories` | Lista categorias pai (exclui system_category) |
| GET | `/categories/{id}` | Detalhe com subcategorias e transacoes |
| POST | `/categories` | Cria (pode ser subcategoria via parent_id) |
| POST | `/categories/{id}/edit` | Edita |
| POST | `/categories/{id}/delete` | Deleta |

---

## Orcamentos

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/budgets` | Lista com filtros (f_category_id, f_month) e sort |
| POST | `/budgets` | Cria (category_id, limit_value, month) |
| POST | `/budgets/{id}/edit` | Edita |
| POST | `/budgets/{id}/delete` | Deleta |

---

## Saldo Manual

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/balance/saldo-inicial` | Define saldo inicial do mes (manual) |
| POST | `/balance/saldo-final` | Define saldo final do mes (manual) |
| POST | `/balance/total-guardado` | Define total guardado do mes (manual) |
| POST | `/balance/reset` | Remove flag manual e recalcula |

---

## Relatorios

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/reports` | Pagina de relatorios (com seletor de ano) |
| GET | `/reports/data/annual` | JSON: dados anuais (entrou/saiu/investiu/sobrou por mes) |
| GET | `/reports/data/categories` | JSON: breakdown por categoria |
| GET | `/reports/data/accounts` | JSON: analytics por conta |

---

## Configuracoes

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/settings` | Pagina de configuracoes |
| POST | `/settings/period` | Atualiza periodo de faturamento |
| POST | `/settings/profile` | Atualiza nome/email |
| POST | `/settings/password` | Altera senha |
