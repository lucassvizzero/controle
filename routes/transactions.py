import calendar
import io
from datetime import date, datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from openpyxl.styles import NamedStyle
from openpyxl.utils import quote_sheetname
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Account, Card, Category, Transaction
from core.schemas import (
    CategoryType,
    Column,
    ComboboxOption,
    CrudField,
    FilterField,
    Permissions,
    TemplateContext,
    UploadSchema,
)
from core.templates import templates
from core.utils import alert_error, alert_success
from routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])
import io

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Account, Card, Category


def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + (month // 12)
    month = (month % 12) + 1
    day = source_date.day
    try:
        return source_date.replace(year=year, month=month, day=day)
    except ValueError:
        last_day = calendar.monthrange(year, month)[1]
        return source_date.replace(year=year, month=month, day=last_day)


@router.get("/transactions")
def get_transactions(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = Query(1),
    per_page: int = Query(10),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    situation: str = Query(None, alias="f_situation"),
    description: str = Query(None, alias="f_description"),
    account_id: int | str = Query(None, alias="f_account_id"),
    card_id: int | str = Query(None, alias="f_card_id"),
    category_id: int | str = Query(None, alias="f_category_id"),
    due_at_start: str = Query(None, alias="f_due_at_start"),
    due_at_end: str = Query(None, alias="f_due_at_end"),
    paid_at_start: str = Query(None, alias="f_paid_at_start"),
    paid_at_end: str = Query(None, alias="f_paid_at_end"),
    category_type: str = Query(None, alias="f_category_type"),
):
    # Base query com joins para poder ordenar por campos relacionados
    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .outerjoin(Card, Transaction.card_id == Card.id)
        .filter(Transaction.user_id == user.id)
    )
    if situation:
        if situation == "1":
            query = query.filter(Transaction.paid_at.isnot(None))
        elif situation == "2":
            query = query.filter(Transaction.paid_at.is_(None))
    if description:
        query = query.filter(Transaction.description.ilike(f"%{description}%"))
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if card_id:
        query = query.filter(Transaction.card_id == card_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if category_type:
        query = query.filter(Category.type == category_type)
    if due_at_start or due_at_end:
        if due_at_start:
            start_date = date.fromisoformat(due_at_start)
            query = query.filter(Transaction.due_at >= start_date)
        if due_at_end:
            end_date = date.fromisoformat(due_at_end)
            query = query.filter(Transaction.due_at <= end_date)
    if paid_at_start or paid_at_end:
        if paid_at_start:
            start_date = date.fromisoformat(paid_at_start)
            query = query.filter(Transaction.paid_at >= start_date)
        if paid_at_end:
            end_date = date.fromisoformat(paid_at_end)
            query = query.filter(Transaction.paid_at <= end_date)

    sort_map = {
        "id": Transaction.id,
        "account": Account.name,
        "category": Category.name,
        "card": Card.name,
        "description": Transaction.description,
        "value": Transaction.value,
        "due_at": Transaction.due_at,
        "paid_at": Transaction.paid_at,
    }
    sort_column = sort_map.get(sort_by, Transaction.id)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    total_count = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()

    columns = [
        Column(label="ID", type="number", sort=True, sort_key="id"),
        Column(label="Conta", type="text", sort=True, sort_key="account"),
        Column(label="Categoria", type="html", sort=True, sort_key="category"),
        Column(label="Cartão", type="text", sort=True, sort_key="card"),
        Column(label="Descrição", type="text", sort=True, sort_key="description"),
        Column(label="Valor", type="currency", sort=True, sort_key="value"),
        Column(label="Vencimento", type="date", sort=True, sort_key="due_at"),
        Column(label="Pago em", type="datetime-local", sort=True, sort_key="paid_at"),
    ]

    values = []
    for t in transactions:
        account_name = t.account.name if t.account else "N/A"
        if t.category and t.category.icon and t.category.color:
            category_html = (
                f"<i class='{t.category.icon} text-xl' style='color:{t.category.color}'></i>"
                f" {t.category.name}"
            )
        elif t.category:
            category_html = t.category.name
        else:
            category_html = "N/A"
        card_name = t.card.name if t.card else ""
        display_value = float(t.value)
        if t.category and t.category.type == CategoryType.expense:
            display_value = -display_value
        values.append(
            [
                t.id,
                account_name,
                category_html,
                card_name,
                t.description or "",
                display_value,
                t.due_at,
                t.paid_at,
            ]
        )

    # Schemas para CRUD e filtros
    account_options = [
        ComboboxOption(value=acc.id, label=acc.name).model_dump()
        for acc in db.query(Account).filter(Account.user_id == user.id).all()
    ]

    category_options = [
        ComboboxOption(
            value=cat.id, label=cat.name if not cat.parent_id else f"{cat.parent.name} > {cat.name}"
        ).model_dump()
        for cat in db.query(Category).filter(Category.user_id == user.id).all()
    ]
    card_options = [
        ComboboxOption(value=c.id, label=c.name).model_dump()
        for c in db.query(Card).filter(Card.user_id == user.id).all()
    ]

    crud_schema = [
        CrudField(
            name="account_id",
            label="Conta",
            type="combobox",
            required=True,
            edit=True,
            options=account_options,
        ),
        CrudField(
            name="category_id",
            label="Categoria",
            type="combobox",
            required=True,
            edit=True,
            options=category_options,
        ),
        CrudField(
            name="card_id",
            label="Cartão",
            type="combobox",
            required=False,
            edit=True,
            options=[{"value": "", "label": "Nenhum"}] + card_options,
        ),
        CrudField(name="description", label="Descrição", type="text", required=False, edit=True),
        CrudField(
            name="value",
            label="Valor",
            type="number",
            required=True,
            edit=True,
            min=0,
            step="0.01",
        ),
        CrudField(name="due_at", label="Vencimento", type="date", required=True, edit=True),
        CrudField(
            name="paid_at", label="Pago em", type="datetime-local", required=False, edit=True
        ),
        CrudField(
            name="is_recurring",
            label="É Recorrente?",
            type="switch",
            required=False,
            edit=True,
        ),
        CrudField(
            name="recurring_frequency",
            label="Frequência Recorrência",
            type="combobox",
            required=False,
            edit=True,
            options=[
                ComboboxOption(value="mensal", label="Mensal"),
                ComboboxOption(value="semanal", label="Semanal"),
                ComboboxOption(value="anual", label="Anual"),
            ],
        ),
        CrudField(
            name="recurring_end_date",
            label="Data Final Recorrência",
            type="date",
            required=False,
            edit=True,
        ),
        CrudField(
            name="is_installment",
            label="É Parcelado?",
            type="switch",
            required=False,
            edit=True,
        ),
        CrudField(
            name="total_installments",
            label="Quantidade Parcelas",
            type="number",
            required=False,
            edit=True,
            min=0,
            step="0",
        ),
        CrudField(
            name="current_installment",
            label="Parcela Atual",
            type="number",
            required=False,
            edit=True,
            min=0,
            step="0",
        ),
    ]

    filter_schema = [
        FilterField(name="description", label="Descrição", type="text"),
        FilterField(
            name="situation",
            label="Situação",
            type="combobox",
            options=[
                ComboboxOption(value="1", label="Paga"),
                ComboboxOption(value="2", label="Não Paga"),
            ],
        ),
        FilterField(
            name="account_id",
            label="Conta",
            type="combobox",
            options=account_options,
        ),
        FilterField(
            name="card_id",
            label="Cartão",
            type="combobox",
            options=card_options,
        ),
        FilterField(
            name="category_id",
            label="Categoria",
            type="combobox",
            options=category_options,
        ),
        FilterField(
            name="category_type",
            label="Tipo",
            type="combobox",
            options=[
                ComboboxOption(value=CategoryType.income.value, label="Receita"),
                ComboboxOption(value=CategoryType.expense.value, label="Despesa"),
                ComboboxOption(value=CategoryType.transfer.value, label="Transferência"),
                ComboboxOption(value=CategoryType.invoice.value, label="Pagamento de Fatura"),
            ],
        ),
        FilterField(name="due_at_start", label="Vencimento de", type="date"),
        FilterField(name="due_at_end", label="Vencimento até", type="date"),
        FilterField(name="paid_at_start", label="Pago de", type="datetime-local"),
        FilterField(name="paid_at_end", label="Pago até", type="datetime-local"),
    ]

    upload_schema = UploadSchema(
        label="Adicionar Transações",
        description="Você deve usar o Modelo de Planilha para preencher os dados corretamente. ",
        file_type="xlsx",
        pre_fields=None,
    )

    permissions = Permissions(add=True, edit=True, delete=True, upload=True, filter=True)

    context = TemplateContext(
        request=request,
        entity="transactions",
        permissions=permissions,
        columns=columns,
        values=values,
        crud_schema=crud_schema,
        filter_schema=filter_schema,
        upload_schema=upload_schema,
        total_count=total_count,
    )
    return templates.TemplateResponse("pages/transactions.html", context.model_dump())


@router.get("/transactions/download-template")
def download_transactions_template(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Gera e retorna um template de planilha Excel para upload de transações."""

    # Consultar dados do banco
    accounts = [a.name for a in db.query(Account).filter(Account.user_id == user.id).all()]
    cards = [c.name for c in db.query(Card).filter(Card.user_id == user.id).all()]
    parent_categories = (
        db.query(Category).filter(Category.user_id == user.id, Category.parent_id.is_(None)).all()
    )
    categories = []
    for parent in parent_categories:
        categories.append(parent.name.strip())
        for sub in parent.subcategories:
            categories.append(parent.name.strip() + " > " + sub.name.strip())

    # Encontrar o tamanho máximo das listas
    max_len = max(len(accounts), len(cards), len(categories))
    accounts += [None] * (max_len - len(accounts))
    cards += [None] * (max_len - len(cards))
    categories += [None] * (max_len - len(categories))

    # Criar DataFrame da aba de Transações
    df_transactions = pd.DataFrame(
        columns=[
            "CONTA",
            "CARTAO",
            "CATEGORIA",
            "DESCRICAO",
            "VALOR",
            "DATA_VENCIMENTO",
            "DATA_PAGAMENTO",
            "É_RECORRENTE?",
            "FREQUENCIA_RECORRENCIA",
            "DATA_FINAL_RECORRENCIA",
            "É_PARCELADO?",
            "QUANTIDADE_PARCELAS",
            "PARCELA_ATUAL",
        ]
    )

    # Criar DataFrame da aba Auxiliar
    df_auxiliar = pd.DataFrame({"CONTA": accounts, "CARTAO": cards, "CATEGORIA": categories})

    # Criar um arquivo Excel na memória
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_transactions.to_excel(writer, sheet_name="Transações", index=False)
        df_auxiliar.to_excel(writer, sheet_name="Auxiliar", index=False)

        wb = writer.book
        ws_transactions = wb["Transações"]

        # Criar estilos para formatação correta
        currency_style = NamedStyle(name="currency", number_format='"R$" #,##0.00')
        integer_style = NamedStyle(name="integer", number_format="0")
        date_style = NamedStyle(name="date", number_format="DD/MM/YYYY")

        if "currency" not in wb.named_styles:
            wb.add_named_style(currency_style)
        if "integer" not in wb.named_styles:
            wb.add_named_style(integer_style)
        if "date" not in wb.named_styles:
            wb.add_named_style(date_style)

        # Definir intervalos das listas auxiliares
        max_accounts = len(accounts) + 1
        max_cards = len(cards) + 1
        max_categories = len(categories) + 1

        account_range = f"{quote_sheetname('Auxiliar')}!$A$2:$A${max_accounts}"
        card_range = f"{quote_sheetname('Auxiliar')}!$B$2:$B${max_cards}"
        category_range = f"{quote_sheetname('Auxiliar')}!$C$2:$C${max_categories}"

        # Criar validações de dados
        dv_sim_nao = DataValidation(type="list", formula1='"SIM,NAO"', allow_blank=True)
        dv_frequencia = DataValidation(
            type="list", formula1='"mensal,semanal,anual"', allow_blank=True
        )
        dv_currency = DataValidation(type="decimal", operator="greaterThan", formula1="0")
        dv_integer = DataValidation(type="whole", operator="greaterThan", formula1="0")
        dv_date = DataValidation(type="date")

        dv_account = DataValidation(type="list", formula1=account_range, allow_blank=False)
        dv_card = DataValidation(type="list", formula1=card_range, allow_blank=True)
        dv_category = DataValidation(type="list", formula1=category_range, allow_blank=False)

        # Adicionar validações ao worksheet
        ws_transactions.add_data_validation(dv_account)
        ws_transactions.add_data_validation(dv_card)
        ws_transactions.add_data_validation(dv_category)
        ws_transactions.add_data_validation(dv_sim_nao)
        ws_transactions.add_data_validation(dv_frequencia)
        ws_transactions.add_data_validation(dv_currency)
        ws_transactions.add_data_validation(dv_integer)
        ws_transactions.add_data_validation(dv_date)

        # Aplicar validações e formatações às células
        for row in range(2, 200):
            ws_transactions[f"A{row}"].value = None  # CONTA
            ws_transactions[f"B{row}"].value = None  # CARTAO
            ws_transactions[f"C{row}"].value = None  # CATEGORIA
            ws_transactions[f"H{row}"].value = "NAO"  # É_RECORRENTE? (default: NAO)
            ws_transactions[f"K{row}"].value = "NAO"  # É_PARCELADO? (default: NAO)

            dv_account.add(ws_transactions[f"A{row}"])
            dv_card.add(ws_transactions[f"B{row}"])
            dv_category.add(ws_transactions[f"C{row}"])
            dv_currency.add(ws_transactions[f"E{row}"])  # VALOR
            dv_date.add(ws_transactions[f"F{row}"])  # DATA_VENCIMENTO
            dv_date.add(ws_transactions[f"G{row}"])  # DATA_PAGAMENTO
            dv_sim_nao.add(ws_transactions[f"H{row}"])  # É_RECORRENTE?
            dv_frequencia.add(ws_transactions[f"I{row}"])  # FREQUENCIA_RECORRENCIA
            dv_date.add(ws_transactions[f"J{row}"])  # DATA_FINAL_RECORRENCIA
            dv_sim_nao.add(ws_transactions[f"K{row}"])  # É_PARCELADO?
            dv_integer.add(ws_transactions[f"L{row}"])  # QUANTIDADE_PARCELAS
            dv_integer.add(ws_transactions[f"M{row}"])  # PARCELA_ATUAL

            # Aplicar estilos nas células
            ws_transactions[f"E{row}"].style = "currency"  # VALOR em BRL
            ws_transactions[f"F{row}"].style = "date"  # DATA_VENCIMENTO
            ws_transactions[f"G{row}"].style = "date"  # DATA_PAGAMENTO
            ws_transactions[f"J{row}"].style = "date"  # DATA_FINAL_RECORRENCIA
            ws_transactions[f"L{row}"].style = "integer"  # QUANTIDADE_PARCELAS
            ws_transactions[f"M{row}"].style = "integer"  # PARCELA_ATUAL

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template_transacoes.xlsx"},
    )


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    """Retorna os dados de uma transação para edição no modal."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        return {"error": "Transação não encontrada"}
    # Retorna sempre o valor absoluto, já que armazenamos como positivo.
    return {
        "account_id": transaction.account_id,
        "category_id": transaction.category_id,
        "card_id": transaction.card_id if transaction.card_id else "",
        "description": transaction.description or "",
        "value": float(transaction.value),
        "due_at": transaction.due_at.isoformat(),
        "paid_at": transaction.paid_at.isoformat() if transaction.paid_at else "",
        "is_recurring": transaction.is_recurring,
        "recurring_frequency": transaction.recurring_frequency,
        "recurring_end_date": (
            transaction.recurring_end_date.isoformat() if transaction.recurring_end_date else ""
        ),
        "is_installment": bool(transaction.installments),
        "total_installments": transaction.installments,
        "current_installment": transaction.current_installment,
    }


@router.post("/transactions")
def create_transaction(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    account_id: int = Form(...),
    category_id: int = Form(...),
    card_id: str = Form(None),
    description: str = Form(""),
    value: float = Form(...),
    due_at: date = Form(...),
    paid_at: str = Form(None),
    is_recurring: bool = Form(False),
    recurring_frequency: str = Form(None),
    recurring_end_date: str = Form(None),
    is_installment: bool = Form(False),
    total_installments: str = Form(None),
    current_installment: str = Form(None),
):
    """Cria uma nova transação. O valor é sempre armazenado como positivo."""
    url_redirect = "/transactions"
    referer = request.headers.get("referer")
    if referer and len(referer.split("?")) > 1:
        url_redirect = url_redirect + f"?{referer.split('?')[1]}"
    account = db.query(Account).get(int(account_id))
    card = None
    if card_id:
        card = db.query(Card).get(int(card_id))

    if not account or (card_id and not card):
        alert_error(request, "Conta ou cartão não encontrados")
        return RedirectResponse(url=url_redirect, status_code=303)

    if is_installment and is_recurring:
        alert_error(request, "Transação não pode ser recorrente e parcelada")
        return RedirectResponse(url=url_redirect, status_code=303)

    if is_installment and (not total_installments or not current_installment):
        alert_error(request, "Transação parcelada deve ter quantidade de parcelas e parcela atual")
        return RedirectResponse(url=url_redirect, status_code=303)

    if is_recurring and not recurring_frequency:
        alert_error(request, "Transação recorrente deve ter uma frequência")
        return RedirectResponse(url=url_redirect, status_code=303)

    paid_at = datetime.fromisoformat(paid_at) if paid_at else None
    recurring_frequency = recurring_frequency if is_recurring else None
    recurring_end_date = (
        date.fromisoformat(recurring_end_date) if is_recurring and recurring_end_date else None
    )
    total_installments = int(total_installments) if is_installment else None
    current_installment = int(current_installment) if is_installment else None

    transactions = create_transactions(
        user,
        db,
        account,
        card,
        category_id,
        description,
        value,
        due_at,
        paid_at,
        is_recurring,
        recurring_frequency,
        recurring_end_date,
        is_installment,
        total_installments,
        current_installment,
    )
    alert_success(request, f"{len(transactions)} Transações criadas com sucesso!")
    return RedirectResponse(url=url_redirect, status_code=303)


@router.post("/transactions/{transaction_id}/edit")
def edit_transaction(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    account_id: int = Form(...),
    category_id: int = Form(...),
    card_id: str = Form(None),
    description: str = Form(""),
    value: float = Form(...),
    due_at: date = Form(...),
    paid_at: str = Form(None),
    is_recurring: bool = Form(False),
    recurring_frequency: str = Form(None),
    recurring_end_date: str = Form(None),
    is_installment: bool = Form(False),
    total_installments: str = Form(None),
    current_installment: str = Form(None),
):
    """Edita uma transação existente. O valor é sempre armazenado como positivo."""
    url_redirect = "/transactions"
    referer = request.headers.get("referer")
    if referer and len(referer.split("?")) > 1:
        url_redirect = url_redirect + f"?{referer.split('?')[1]}"
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        alert_error(request, "Transação não encontrada")
        return RedirectResponse(url=url_redirect, status_code=303)

    if is_installment and is_recurring:
        alert_error(request, "Transação não pode ser recorrente e parcelada")
        return RedirectResponse(url=url_redirect, status_code=303)

    if is_installment and (not total_installments or not current_installment):
        alert_error(request, "Transação parcelada deve ter quantidade de parcelas e parcela atual")
        return RedirectResponse(url=url_redirect, status_code=303)

    if is_recurring and not recurring_frequency:
        alert_error(request, "Transação recorrente deve ter uma frequência")
        return RedirectResponse(url=url_redirect, status_code=303)

    paid_at = datetime.fromisoformat(paid_at) if paid_at else None
    recurring_frequency = recurring_frequency if is_recurring else None
    recurring_end_date = (
        date.fromisoformat(recurring_end_date) if is_recurring and recurring_end_date else None
    )
    total_installments = int(total_installments) if is_installment else None
    current_installment = int(current_installment) if is_installment else None

    transaction.account_id = account_id if account_id else None
    transaction.category_id = category_id
    transaction.card_id = card_id if card_id else None
    transaction.description = description
    transaction.value = abs(value)
    transaction.due_at = due_at
    transaction.paid_at = paid_at
    db.commit()

    if transaction.is_recurring and not is_recurring:
        print("Deixou de ser recorrente")
        # Delete all future recurring transactions
        cleanup_next_transactions(db, transaction.id)
        transaction.is_recurring = False
        transaction.recurring_frequency = None
        transaction.recurring_end_date = None
        db.commit()
        if transaction.parent_id:
            parent_id = transaction.parent_id
            while parent_id:
                parent_transaction = (
                    db.query(Transaction).filter(Transaction.parent_id == parent_id).first()
                )
                if parent_transaction:
                    parent_transaction.recurring_end_date = transaction.due_at
                    if parent_transaction.parent_id:
                        parent_id = parent_transaction.parent_id
                    else:
                        parent_id = None
                    db.commit()
                else:
                    parent_id = None

    elif is_recurring:
        print("É recorrente")
        # Create all future recurring transactions
        create_transactions(
            user,
            db,
            transaction.account,
            transaction.card,
            transaction.category_id,
            transaction.description,
            transaction.value,
            transaction.due_at,
            transaction.paid_at,
            is_recurring,
            recurring_frequency,
            recurring_end_date,
            is_installment,
            total_installments,
            current_installment,
            parent_id=transaction.parent_id,
        )
        # delete old transaction
        db.delete(transaction)
        db.commit()

    if transaction.installments and not is_installment:
        print("Deixou de ser parcelado")
        # Delete all future installment transactions
        cleanup_next_transactions(db, transaction.id)
        description = description.split(") ")[1] if description.startswith("(") else description
        if transaction.parent_id:
            parent_id = transaction.parent_id
            total_installments = transaction.current_installment - 1
            modify_parent_transaction_info(db, description, total_installments, parent_id)

        db.delete(transaction)
        db.commit()

    elif is_installment:
        print("É parcelado")
        # Create all future installment transactions
        # Create all future recurring transactions
        description = description.split(") ")[1] if description.startswith("(") else description
        if transaction.parent_id:
            parent_id = transaction.parent_id
            modify_parent_transaction_info(db, description, total_installments, parent_id)

        create_transactions(
            user,
            db,
            transaction.account,
            transaction.card,
            transaction.category_id,
            description,
            transaction.value,
            transaction.due_at,
            transaction.paid_at,
            is_recurring,
            recurring_frequency,
            recurring_end_date,
            is_installment,
            total_installments,
            current_installment,
            parent_id=transaction.parent_id,
        )
        # delete old transaction
        db.delete(transaction)
        db.commit()
    return RedirectResponse(url=url_redirect, status_code=303)


def modify_parent_transaction_info(db, description, total_installments, parent_id):
    while parent_id:
        parent_transaction = db.query(Transaction).filter(Transaction.id == parent_id).first()
        if parent_transaction:
            parent_transaction.description = (
                f"({parent_transaction.current_installment}/{total_installments}) {description}"
            )
            parent_transaction.installments = total_installments
            if parent_transaction.parent_id:
                parent_id = parent_transaction.parent_id
            else:
                parent_id = None
            db.commit()
        else:
            parent_id = None


@router.post("/transactions/{transaction_id}/delete")
def delete_transaction(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Exclui uma transação."""
    url_redirect = "/transactions"
    referer = request.headers.get("referer")
    if referer and len(referer.split("?")) > 1:
        url_redirect = url_redirect + f"?{referer.split('?')[1]}"

    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if not transaction:
        alert_error(request, "Transação não encontrada")
        return RedirectResponse(url=url_redirect, status_code=303)
    try:
        if transaction.installments:
            description = (
                transaction.description.split(") ")[1]
                if transaction.description.startswith("(")
                else transaction.description
            )
            total_installments = transaction.current_installment - 1
            parent_id = transaction.parent_id
            modify_parent_transaction_info(db, description, total_installments, parent_id)

        cleanup_next_transactions(db, transaction.id)
        db.delete(transaction)
        db.commit()
        alert_success(request, "Transação excluída com sucesso!")
    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao excluir transação: {str(e)}")
    return RedirectResponse(url=url_redirect, status_code=303)


@router.post("/transactions/upload")
def upload_transactions(
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """
    Importa transações em massa via arquivo XLSX (Usar o Modelo).
    - Se for recorrente e não tiver data final, criar até o final do ano.
    - Se for parcelado, adicionar a parcela na descrição e criar as transações das parcelas restantes.
    """
    try:
        # Ler arquivo Excel
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name="Transações")

        # Buscar listas auxiliares
        account_names = {
            a.name: a for a in db.query(Account).filter(Account.user_id == user.id).all()
        }
        card_names = {c.name: c for c in db.query(Card).filter(Card.user_id == user.id).all()}
        category_names = {
            c.name.strip() if not c.parent_id else f"{c.parent.name} > {c.name}".strip(): c.id
            for c in db.query(Category).filter(Category.user_id == user.id).all()
        }

        transactions = []
        for index, row in df.iterrows():
            if pd.isna(row["CONTA"]) or pd.isna(row["CATEGORIA"]) or pd.isna(row["VALOR"]):
                continue

            account = account_names.get(row["CONTA"])
            if not account:
                alert_error(request, f"Linha[{index+2}] Conta inválida")
                return

            card = card_names.get(row["CARTAO"]) if pd.notna(row["CARTAO"]) else None
            if card and card.account_id != account.id:
                alert_error(request, f"Linha[{index+2}] Cartão inválido")
                return

            category_id = category_names.get(row["CATEGORIA"].strip())
            if not category_id:
                alert_error(request, f"Linha[{index+2}] Categoria inválida")
                return

            description = row["DESCRICAO"]
            value = row["VALOR"]
            due_at = row["DATA_VENCIMENTO"]
            paid_at = row["DATA_PAGAMENTO"] if pd.notna(row["DATA_PAGAMENTO"]) else None
            is_recurring = str(row["É_RECORRENTE?"]).strip().lower() == "sim"

            # Tratar frequência de recorrência corretamente
            recurring_frequency = row["FREQUENCIA_RECORRENCIA"] if is_recurring else None
            if pd.isna(recurring_frequency) or recurring_frequency not in [
                "semanal",
                "mensal",
                "anual",
            ]:
                recurring_frequency = None

            recurring_end_date = row["DATA_FINAL_RECORRENCIA"] if is_recurring else None
            if pd.isna(recurring_end_date):
                recurring_end_date = None
            is_installment = str(row["É_PARCELADO?"]).strip().lower() == "sim"
            total_installments = (
                int(row["QUANTIDADE_PARCELAS"])
                if is_installment and pd.notna(row["QUANTIDADE_PARCELAS"])
                else None
            )
            current_installment = (
                int(row["PARCELA_ATUAL"])
                if is_installment and pd.notna(row["PARCELA_ATUAL"])
                else None
            )

            if is_installment and is_recurring:
                alert_error(
                    request, f"Linha[{index+2}] Transação não pode ser recorrente e parcelada"
                )
                return

            transactions.extend(
                create_transactions(
                    user,
                    db,
                    account,
                    card,
                    category_id,
                    description,
                    value,
                    due_at,
                    paid_at,
                    is_recurring,
                    recurring_frequency,
                    recurring_end_date,
                    is_installment,
                    total_installments,
                    current_installment,
                )
            )

        # Salvar transações no banco
        alert_success(request, f"{len(transactions)} Transações importadas com sucesso!")

    except Exception as e:
        db.rollback()
        alert_error(request, f"Erro ao processar upload: {str(e)}")
        print(f"Erro ao processar upload: {e}")

    return


def cleanup_next_transactions(db, parent_id):
    while parent_id:
        sub_transaction = (
            db.query(Transaction).filter(Transaction.parent_id == parent_id).one_or_none()
        )
        if sub_transaction:
            parent_id = sub_transaction.id
            db.delete(sub_transaction)
            db.commit()
        else:
            parent_id = None


def create_transactions(
    user,
    db,
    account,
    card,
    category_id,
    description,
    value,
    due_at,
    paid_at,
    is_recurring,
    recurring_frequency,
    recurring_end_date,
    is_installment,
    total_installments,
    current_installment,
    parent_id=None,
):
    transactions = []
    today = datetime.today()

    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        card_id=card.id if card else None,
        category_id=category_id,
        description=(
            f"({current_installment}/{total_installments}) {description}"
            if is_installment
            else description
        ),
        value=value,
        due_at=due_at,
        paid_at=paid_at,
        is_recurring=is_recurring,
        recurring_frequency=recurring_frequency,
        installments=total_installments,
        current_installment=current_installment,
        parent_id=parent_id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    transactions.append(transaction)
    # Criar transações recorrentes até o fim do ano
    if is_recurring and recurring_frequency:
        last_due = due_at
        while not recurring_end_date or last_due.year == today.year:
            if recurring_frequency == "mensal":
                last_due = add_months(last_due, 1)
            elif recurring_frequency == "semanal":
                last_due += timedelta(days=7)
            elif recurring_frequency == "anual":
                last_due = add_months(last_due, 12)
            else:
                break  # Frequência não reconhecida
            if int(last_due.year) > int(today.year):
                break

                # Verificar se ultrapassou a data final, se houver
            if recurring_end_date and last_due > recurring_end_date:
                break

            transaction = Transaction(
                user_id=user.id,
                account_id=account.id,
                card_id=card.id if card else None,
                category_id=category_id,
                description=description,
                value=value,
                due_at=last_due,
                is_recurring=True,
                recurring_frequency=recurring_frequency,
                parent_id=transactions[-1].id,
            )
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            transactions.append(transaction)

    # Criar parcelas futuras
    if is_installment and total_installments and current_installment:
        for installment in range(current_installment + 1, total_installments + 1):
            months_to_add = installment - current_installment
            new_due_at = add_months(due_at, months_to_add)
            transaction = Transaction(
                user_id=user.id,
                account_id=account.id,
                card_id=card.id if card else None,
                category_id=category_id,
                description=f"({installment}/{total_installments}) {description}",
                value=value,
                due_at=new_due_at,
                is_recurring=False,
                installments=total_installments,
                current_installment=installment,
                parent_id=transactions[-1].id,
            )
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            transactions.append(transaction)
    return transactions
