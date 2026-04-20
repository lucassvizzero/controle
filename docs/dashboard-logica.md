# Dashboard - Logica Detalhada

O dashboard (`routes/index.py`, `GET /`) e a pagina mais complexa do sistema. Este doc explica o fluxo completo.

---

## 1. Determinacao do Mes Nominal

Se `year` e `month` nao sao passados na query string:

```python
today = date.today()
year, month = today.year, today.month

# Se o periodo cruza meses (ex: 20->19) e estamos apos o dia de inicio,
# o mes nominal e o proximo
if p_start > p_end:
    if today.day >= p_start:
        year, month = shift_month(year, month, 1)
```

Exemplo com periodo 20-19:
- Dia 19/Abr -> mes nominal = Abril (periodo 20/Mar a 19/Abr)
- Dia 20/Abr -> mes nominal = Maio (periodo 20/Abr a 19/Mai)

---

## 2. Calculo do Periodo

`get_period_range(year, month, first_day, last_day)`:

- Se `first_day > last_day` (cruza meses): start = dia `first_day` do mes anterior
- `end_date` = dia `last_day` do mes nominal, as 23:59:59.999999

Exemplo: Mes 5, periodo 20-19 -> 20/Abr 00:00 ate 19/Mai 23:59

---

## 3. Query de Transacoes

### 3.1 Transacoes sem Cartao

Filtro simples: `card_id IS NULL AND due_at BETWEEN start_date AND end_date`

### 3.2 Transacoes de Cartao (Faturas)

Para cada cartao, calcula o range da fatura que CAI dentro do periodo do dashboard:

```python
for card in cards:
    if p_start > p_end:
        if card.due_day < p_start:
            year_card, month_card = shift_month(year, month, -1)
        else:
            year_card, month_card = shift_month(year, month, -2)
    else:
        if card.due_day < p_start:
            year_card, month_card = year, month
        else:
            year_card, month_card = shift_month(year, month, -1)

    invoice_start = date(year_card, month_card, close_day)
    invoice_end = date(year_card+1m, month_card+1m, close_day - 1)
```

**Logica**: O `due_day` do cartao determina em qual mes a fatura vence. Se o `due_day` e menor que `p_start`, a fatura ja vence "dentro" do periodo sem precisar voltar muito; se e maior/igual, precisa voltar um mes a mais.

**Exemplo**: Mes 5, periodo 20-19, Santander (due=21, close=14):
- `due_day=21 >= p_start=20` -> volta 2 meses: (2026, 3)
- Range: 14/Mar a 13/Abr
- Fatura gerada: vencimento 21/Abr (dentro do periodo 20/Abr a 19/Mai)

### 3.3 Transacoes Pagas vs Pendentes

**Pagas** (`transacoes_efetuada_all`):
- `paid_at IS NOT NULL`
- `paid_at BETWEEN start_date AND end_date`
- Inclui todas transacoes (com e sem cartao que passam nos filtros)

**Pendentes** (`transacoes_pendente_all`):
- `paid_at IS NULL`
- Usa o `query_or` com filtros de cartao por range de datas

---

## 4. Agrupamento em Faturas

`convert_index_transactions(transactions)`:

1. Separa transacoes com `card_id` das sem cartao
2. Para cada cartao, ordena por `due_at`
3. Determina o mes da fatura: se `due_at.day >= close_day`, a compra vai para o mes seguinte
4. Cria `TransactionIndexOut` com `is_card_invoice=True`:
   - `description`: "Fatura {card_name} - {Mes/Ano}"
   - `value`: Soma das transacoes (expense soma, income subtrai)
   - `due_at`: Dia do vencimento no mes calculado
   - `transactions`: Lista com detalhes de cada transacao da fatura
5. Faturas pagas e nao-pagas ficam em entradas separadas (sufixo "-paid")

---

## 5. Resumos Financeiros

```python
entrou = sum(t.value for t in pagas if t.category.type == income and card_id is None)
saiu = sum(t.value for t in pagas if t.category.type == expense)
investiu = sum(t.value for t in pagas if t.category.type == investment)
credito_cartao = sum(t.value for t in pagas if t.category.type == income and card_id is not None)
saiu = saiu - credito_cartao
sobrou = entrou - (saiu + investiu)
```

- `credito_cartao` e subtraido de `saiu` (creditos na fatura reduzem o gasto)
- Preview: soma pendentes + efetuadas para dar uma projecao

---

## 6. Saldo e Total Guardado

Apos calcular os resumos:

```python
balance = recalculate_balance(db, user_id, year, month, entrou, saiu, investiu)
savings = recalculate_savings(db, user_id, year, month, investiu)
db.commit()
```

- `saldo_inicial`: Herdado do `saldo_final` do mes anterior (se nao manual)
- `saldo_final`: `saldo_inicial + entrou - saiu - investiu` (se nao manual)
- `total_guardado`: Acumulado do mes anterior + investiu (se nao manual)

---

## 7. Orcamentos

Busca budgets do mes nominal e calcula progresso:

1. Agrupa orcamentos por categoria pai (root category)
2. Para cada grupo, calcula `total_limit`, `total_spent`, `progress`
3. Categorias sem orcamento mas com gastos tambem aparecem (limit=0)
4. Cor da barra: azul->verde (0-100%), verde->vermelho (100-150%)

---

## 8. Variaveis do Template

O template recebe ~50 variaveis incluindo:

- Navegacao: year, month, month_name, prev_year/month, next_year/month
- Periodo: start_date, end_date
- Resumos: entrou, saiu, investiu, sobrou, *_preview
- Saldo: saldo_inicial, saldo_final, total_guardado (+ flags manual)
- Transacoes: transacoes_efetuadas, transacoes_pendentes (ja paginadas)
- Paginacao: total_paid, paid_page, paid_per_page, total_pending, pending_page, pending_per_page
- Orcamento: orcamento_percent, budgets_parent_info
- CRUD: permissions, entity, crud_schema
