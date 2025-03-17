from passlib.context import CryptContext

from core.database import get_db
from core.models import Account, Card, Category, User
from core.schemas import BankName, BrandName


def fixtures():
    """Cria dados iniciais para testes: usuário, contas, cartões, categorias (pais e subcategorias),
    transações e orçamentos, incluindo as categorias solicitadas."""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = next(get_db())

    # Criar usuário
    user = User(
        email="lucas@lucas.com",
        name="Lucas",
        username="lucas",
        password=pwd_context.hash("123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Criar Contas Bancárias
    accounts = [
        Account(
            user_id=user.id,
            name="Conta Corrente Santander",
            bank=BankName.santander,
            balance=0.00,
        ),
        Account(
            user_id=user.id,
            name="Conta Corrente NuBank",
            bank=BankName.nubank,
            balance=0.00,
        ),
        Account(
            user_id=user.id,
            name="Carteira Digital C6 Bank",
            bank=BankName.c6bank,
            balance=0.00,
        ),
    ]
    db.add_all(accounts)
    db.commit()

    # Criar Cartões de Crédito
    cards = [
        Card(
            user_id=user.id,
            account_id=accounts[0].id,
            name="Santander Unique",
            brand=BrandName.visa,
            close_day=14,
            due_day=21,
            credit_limit=30500.00,
        ),
        Card(
            user_id=user.id,
            account_id=accounts[1].id,
            name="Nubank Ultravioleta",
            brand=BrandName.mastercard,
            close_day=21,
            due_day=28,
            credit_limit=30600.00,
        ),
        Card(
            user_id=user.id,
            account_id=accounts[2].id,
            name="C6 Carbon",
            brand=BrandName.mastercard,
            close_day=14,
            due_day=20,
            credit_limit=11000.00,
        ),
    ]
    db.add_all(cards)
    db.commit()

    # Criar Categorias principais (pais)
    # 1. Salário (sem subcategorias, é uma entrada)
    cat_salario = Category(
        user_id=user.id,
        name="Salário",
        type="income",
        icon="fas fa-wallet",
        color="#4CAF50",
    )

    # 2. Alimentação (despesa)
    cat_alimentacao = Category(
        user_id=user.id,
        name="Alimentação",
        type="expense",
        icon="fas fa-utensils",
        color="#FF0000",
    )
    # 3. Casa (despesa)
    cat_casa = Category(
        user_id=user.id,
        name="Casa",
        type="expense",
        icon="fas fa-home",
        color="#2196F3",
    )
    # 4. Carro (despesa)
    cat_carro = Category(
        user_id=user.id,
        name="Carro",
        type="expense",
        icon="fas fa-car",
        color="#FFC107",
    )
    # 5. Pais (despesa)
    cat_pais = Category(
        user_id=user.id,
        name="Pais",
        type="expense",
        icon="fas fa-user-friends",
        color="#8E24AA",
    )
    # 6. Filhos (despesa)
    cat_filhos = Category(
        user_id=user.id,
        name="Filhos",
        type="expense",
        icon="fas fa-child",
        color="#43A047",
    )
    # 7. Cachorros (despesa)
    cat_cachorros = Category(
        user_id=user.id,
        name="Cachorros",
        type="expense",
        icon="fas fa-dog",
        color="#FF5722",
    )
    # 8. Serviços (despesa)
    cat_servicos = Category(
        user_id=user.id,
        name="Serviços",
        type="expense",
        icon="fas fa-concierge-bell",
        color="#9E9D24",
    )

    # 9. Assinaturas (despesa)
    cat_assinaturas = Category(
        user_id=user.id,
        name="Assinaturas",
        type="expense",
        icon="fas fa-file-contract",
        color="#3F51B5",
    )
    # 10. Viagem (despesa)
    cat_viagem = Category(
        user_id=user.id,
        name="Viagem",
        type="expense",
        icon="fas fa-suitcase-rolling",
        color="#795548",
    )
    # 11. Lazer (despesa)
    cat_lazer = Category(
        user_id=user.id,
        name="Lazer",
        type="expense",
        icon="fas fa-glass-cheers",
        color="#E91E63",
    )
    # 12. Outras Entradas (entrada)
    cat_outras_entradas = Category(
        user_id=user.id,
        name="Outras Entradas",
        type="income",
        icon="fas fa-plus-circle",
        color="#4CAF50",
    )
    # 13. Outras Saídas (despesa)
    cat_outras_saidas = Category(
        user_id=user.id,
        name="Outras Saídas",
        type="expense",
        icon="fas fa-minus-circle",
        color="#F44336",
    )
    cat_banco = Category(
        user_id=user.id,
        name="Banco",
        type="expense",
        icon="fas fa-university",
        color="#FF5722",
    )

    parent_categories = [
        cat_salario,
        cat_alimentacao,
        cat_casa,
        cat_carro,
        cat_pais,
        cat_filhos,
        cat_cachorros,
        cat_servicos,
        cat_assinaturas,
        cat_viagem,
        cat_lazer,
        cat_outras_entradas,
        cat_outras_saidas,
        cat_banco,
    ]
    db.add_all(parent_categories)
    db.commit()
    for cat in parent_categories:
        db.refresh(cat)

    # Criar Subcategorias
    subcategories = [
        # Alimentação
        Category(
            user_id=user.id,
            name="Supermercado",
            type="expense",
            icon="fas fa-shopping-cart",
            color="#E53935",
            parent_id=cat_alimentacao.id,
        ),
        Category(
            user_id=user.id,
            name="IFood",
            type="expense",
            icon="fas fa-pizza-slice",
            color="#D32F2F",
            parent_id=cat_alimentacao.id,
        ),
        Category(
            user_id=user.id,
            name="Restaurante",
            type="expense",
            icon="fas fa-utensils",
            color="#C62828",
            parent_id=cat_alimentacao.id,
        ),
        Category(
            user_id=user.id,
            name="Outros",
            type="expense",
            icon="fas fa-concierge-bell",
            color="#B71C1C",
            parent_id=cat_alimentacao.id,
        ),
        # Casa
        Category(
            user_id=user.id,
            name="DAE",
            type="expense",
            icon="fas fa-water",
            color="#1976D2",
            parent_id=cat_casa.id,
        ),
        Category(
            user_id=user.id,
            name="CPFL",
            type="expense",
            icon="fas fa-lightbulb",
            color="#1565C0",
            parent_id=cat_casa.id,
        ),
        Category(
            user_id=user.id,
            name="Internet/Celular",
            type="expense",
            icon="fas fa-wifi",
            color="#0D47A1",
            parent_id=cat_casa.id,
        ),
        Category(
            user_id=user.id,
            name="Seguro",
            type="expense",
            icon="fas fa-shield-alt",
            color="#0D47A1",
            parent_id=cat_casa.id,
        ),
        Category(
            user_id=user.id,
            name="Condomínio",
            type="expense",
            icon="fas fa-building",
            color="#1565C0",
            parent_id=cat_casa.id,
        ),
        Category(
            user_id=user.id,
            name="IPTU",
            type="expense",
            icon="fas fa-landmark",
            color="#1976D2",
            parent_id=cat_casa.id,
        ),
        Category(
            user_id=user.id,
            name="Manutenção",
            type="expense",
            icon="fas fa-tools",
            color="#1E88E5",
            parent_id=cat_casa.id,
        ),
        # Carro
        Category(
            user_id=user.id,
            name="Combustivel",
            type="expense",
            icon="fas fa-gas-pump",
            color="#F57C00",
            parent_id=cat_carro.id,
        ),
        Category(
            user_id=user.id,
            name="Seguro",
            type="expense",
            icon="fas fa-shield-alt",
            color="#EF6C00",
            parent_id=cat_carro.id,
        ),
        Category(
            user_id=user.id,
            name="IPVA",
            type="expense",
            icon="fas fa-file-invoice-dollar",
            color="#E65100",
            parent_id=cat_carro.id,
        ),
        Category(
            user_id=user.id,
            name="Manutenção",
            type="expense",
            icon="fas fa-tools",
            color="#BF360C",
            parent_id=cat_carro.id,
        ),
        # Pais
        Category(
            user_id=user.id,
            name="Farmácia",
            type="expense",
            icon="fas fa-prescription-bottle-alt",
            color="#6A1B9A",
            parent_id=cat_pais.id,
        ),
        Category(
            user_id=user.id,
            name="Consultas Médicas",
            type="expense",
            icon="fas fa-user-md",
            color="#4A148C",
            parent_id=cat_pais.id,
        ),
        Category(
            user_id=user.id,
            name="Gastos Esseciais",
            type="expense",
            icon="fas fa-shopping-basket",
            color="#311B92",
            parent_id=cat_pais.id,
        ),
        Category(
            user_id=user.id,
            name="Gastos",
            type="expense",
            icon="fas fa-money-bill-wave",
            color="#283593",
            parent_id=cat_pais.id,
        ),
        # Filhos
        Category(
            user_id=user.id,
            name="Farmácia",
            type="expense",
            icon="fas fa-prescription-bottle-alt",
            color="#388E3C",
            parent_id=cat_filhos.id,
        ),
        Category(
            user_id=user.id,
            name="Consultas Médicas",
            type="expense",
            icon="fas fa-user-md",
            color="#2E7D32",
            parent_id=cat_filhos.id,
        ),
        Category(
            user_id=user.id,
            name="Plano de Saúde",
            type="expense",
            icon="fas fa-notes-medical",
            color="#1B5E20",
            parent_id=cat_filhos.id,
        ),
        Category(
            user_id=user.id,
            name="Escola",
            type="expense",
            icon="fas fa-school",
            color="#66BB6A",
            parent_id=cat_filhos.id,
        ),
        Category(
            user_id=user.id,
            name="Atividades Extras",
            type="expense",
            icon="fas fa-futbol",
            color="#81C784",
            parent_id=cat_filhos.id,
        ),
        Category(
            user_id=user.id,
            name="Gastos Esseciais",
            type="expense",
            icon="fas fa-shopping-basket",
            color="#A5D6A7",
            parent_id=cat_filhos.id,
        ),
        Category(
            user_id=user.id,
            name="Gastos",
            type="expense",
            icon="fas fa-money-bill-wave",
            color="#C8E6C9",
            parent_id=cat_filhos.id,
        ),
        # Cachorros
        Category(
            user_id=user.id,
            name="Veterinário",
            type="expense",
            icon="fas fa-user-md",
            color="#E64A19",
            parent_id=cat_cachorros.id,
        ),
        Category(
            user_id=user.id,
            name="Ração",
            type="expense",
            icon="fas fa-drumstick-bite",
            color="#D84315",
            parent_id=cat_cachorros.id,
        ),
        Category(
            user_id=user.id,
            name="Banho",
            type="expense",
            icon="fas fa-bath",
            color="#BF360C",
            parent_id=cat_cachorros.id,
        ),
        Category(
            user_id=user.id,
            name="Gastos Esseciais",
            type="expense",
            icon="fas fa-shopping-basket",
            color="#FF7043",
            parent_id=cat_cachorros.id,
        ),
        Category(
            user_id=user.id,
            name="Gastos",
            type="expense",
            icon="fas fa-money-bill-wave",
            color="#F4511E",
            parent_id=cat_cachorros.id,
        ),
        # Serviços
        Category(
            user_id=user.id,
            name="Faxina",
            type="expense",
            icon="fas fa-broom",
            color="#AFB42B",
            parent_id=cat_servicos.id,
        ),
        Category(
            user_id=user.id,
            name="Jardinagem",
            type="expense",
            icon="fas fa-tree",
            color="#827717",
            parent_id=cat_servicos.id,
        ),
        Category(
            user_id=user.id,
            name="Baba",
            type="expense",
            icon="fas fa-child",
            color="#FBC02D",
            parent_id=cat_servicos.id,
        ),
        Category(
            user_id=user.id,
            name="Uber",
            type="expense",
            icon="fas fa-taxi",
            color="#FDD835",
            parent_id=cat_servicos.id,
        ),
        # Assinaturas
        Category(
            user_id=user.id,
            name="Spotify",
            type="expense",
            icon="fab fa-spotify",
            color="#1DB954",
            parent_id=cat_assinaturas.id,
        ),
        Category(
            user_id=user.id,
            name="Prime",
            type="expense",
            icon="fab fa-amazon",
            color="#FF9900",
            parent_id=cat_assinaturas.id,
        ),
        Category(
            user_id=user.id,
            name="OpenAPi",
            type="expense",
            icon="fas fa-code",
            color="#607D8B",
            parent_id=cat_assinaturas.id,
        ),
        Category(
            user_id=user.id,
            name="Github",
            type="expense",
            icon="fab fa-github",
            color="#24292E",
            parent_id=cat_assinaturas.id,
        ),
        Category(
            user_id=user.id,
            name="Google Cloud",
            type="expense",
            icon="fab fa-google",
            color="#4285F4",
            parent_id=cat_assinaturas.id,
        ),
        Category(
            user_id=user.id,
            name="ICloud",
            type="expense",
            icon="fab fa-apple",
            color="#A2AAAD",
            parent_id=cat_assinaturas.id,
        ),
        Category(
            user_id=user.id,
            name="Outros",
            type="expense",
            icon="fas fa-ellipsis-h",
            color="#607D8B",
            parent_id=cat_assinaturas.id,
        ),
        # Viagem
        Category(
            user_id=user.id,
            name="Caixinha",
            type="expense",
            icon="fas fa-piggy-bank",
            color="#6D4C41",
            parent_id=cat_viagem.id,
        ),
        Category(
            user_id=user.id,
            name="Passagem",
            type="expense",
            icon="fas fa-ticket-alt",
            color="#5D4037",
            parent_id=cat_viagem.id,
        ),
        Category(
            user_id=user.id,
            name="Hospedagem",
            type="expense",
            icon="fas fa-hotel",
            color="#4E342E",
            parent_id=cat_viagem.id,
        ),
        Category(
            user_id=user.id,
            name="Alimentação",
            type="expense",
            icon="fas fa-utensils",
            color="#BF360C",
            parent_id=cat_viagem.id,
        ),
        Category(
            user_id=user.id,
            name="Passeios",
            type="expense",
            icon="fas fa-map-marked-alt",
            color="#3E2723",
            parent_id=cat_viagem.id,
        ),
        Category(
            user_id=user.id,
            name="Compras",
            type="expense",
            icon="fas fa-shopping-bag",
            color="#FF5722",
            parent_id=cat_viagem.id,
        ),
        Category(
            user_id=user.id,
            name="Transporte",
            type="expense",
            icon="fas fa-bus",
            color="#E64A19",
            parent_id=cat_viagem.id,
        ),
        Category(
            user_id=user.id,
            name="Outros",
            type="expense",
            icon="fas fa-ellipsis-h",
            color="#757575",
            parent_id=cat_viagem.id,
        ),
        # Lazer
        Category(
            user_id=user.id,
            name="Encontros",
            type="expense",
            icon="fas fa-handshake",
            color="#AD1457",
            parent_id=cat_lazer.id,
        ),
        Category(
            user_id=user.id,
            name="Passeio em Família",
            type="expense",
            icon="fas fa-users",
            color="#C2185B",
            parent_id=cat_lazer.id,
        ),
        Category(
            user_id=user.id,
            name="Sair com Amigos",
            type="expense",
            icon="fas fa-user-friends",
            color="#880E4F",
            parent_id=cat_lazer.id,
        ),
        # Banco
        Category(
            user_id=user.id,
            name="Tarifa Cartão",
            type="expense",
            icon="fas fa-money-check-alt",
            color="#FF5722",
            parent_id=cat_banco.id,
        ),
        Category(
            user_id=user.id,
            name="Tarifa Conta",
            type="expense",
            icon="fas fa-money-check-alt",
            color="#FF5722",
            parent_id=cat_banco.id,
        ),
        Category(
            user_id=user.id,
            name="Juros",
            type="expense",
            icon="fas fa-money-check-alt",
            color="#FF5722",
            parent_id=cat_banco.id,
        ),
        Category(
            user_id=user.id,
            name="Impostos",
            type="expense",
            icon="fas fa-money-check-alt",
            color="#FF5722",
            parent_id=cat_banco.id,
        ),
        Category(
            user_id=user.id,
            name="SimplesNacional",
            type="expense",
            icon="fas fa-money-check-alt",
            color="#FF5722",
            parent_id=cat_banco.id,
        ),
        Category(
            user_id=user.id,
            name="Seguro",
            type="expense",
            icon="fas fa-money-check-alt",
            color="#FF5722",
            parent_id=cat_banco.id,
        ),
    ]
    db.add_all(subcategories)
    db.commit()

    # # Criar transações aleatórias para todas as categorias (pais e subcategorias)
    # transactions = [
    #     Transaction(
    #         user_id=user.id,
    #         account_id=accounts[0].id,
    #         category_id=parent_categories[0].id,
    #         description=f"Movimentação para {parent_categories[0].name}",
    #         value=25000,
    #         due_day=date.today(),
    #         paid_at=datetime.now(),
    #         is_recurring=False,
    #     )
    # ]
    # for _ in range(60):
    #     account = random.choice(accounts)
    #     category = random.choice(parent_categories + subcategories)
    #     if category.type == "income":
    #         continue

    #     amount = round(random.uniform(50, 1000), 2)
    #     available_cards = [c.id for c in cards if c.account_id == account.id] + [None]

    #     card_id = random.choice(available_cards) if available_cards else None
    #     is_recurring = random.choice([True, False])
    #     recurring_frequency = random.choice(["mensal", "semanal"]) if is_recurring else None
    #     installments = random.choice([3, 6, 10, 12]) if card_id else None
    #     current_installment = (
    #         random.choice([x for x in range(1, installments + 1)]) if installments else None
    #     )
    #     transaction = Transaction(
    #         user_id=user.id,
    #         account_id=account.id,
    #         card_id=card_id,
    #         category_id=category.id,
    #         description=(
    #             f"Movimentação para {category.name}"
    #             if not card_id
    #             else f"Parcela {current_installment}/{installments} de {category.name}"
    #         ),
    #         value=amount,
    #         due_day=date.today() - timedelta(days=random.randint(-5, 15)),
    #         paid_at=(
    #             datetime.now() - timedelta(days=random.randint(0, 15))
    #             if not card_id and random.choice([True, True, True, False])
    #             else None
    #         ),
    #         is_recurring=is_recurring,
    #         recurring_frequency=recurring_frequency,
    #         installments=installments,
    #         current_installment=current_installment,
    #     )
    #     transactions.append(transaction)
    #     if is_recurring:
    #         print(f"Transação recorrente: {transaction.description}")
    #         if not installments and recurring_frequency == "mensal":

    #             for _ in range(1, 6):
    #                 last_transaction = transactions[-1]
    #                 transaction = Transaction(
    #                     user_id=user.id,
    #                     account_id=account.id,
    #                     card_id=card_id,
    #                     category_id=category.id,
    #                     description=f"Movimentação para {category.name}",
    #                     value=amount,
    #                     due_day=last_transaction.due_day + timedelta(days=30),
    #                     paid_at=None,
    #                     is_recurring=is_recurring,
    #                     recurring_frequency=recurring_frequency,
    #                     installments=installments,
    #                     current_installment=current_installment,
    #                     parent_id=last_transaction.id,
    #                 )
    #                 transactions.append(transaction)
    #         elif not installments and recurring_frequency == "semanal":
    #             print(f"Transação semanal: {transaction.description}")
    #             for _ in range(1, 24):
    #                 last_transaction = transactions[-1]
    #                 transaction = Transaction(
    #                     user_id=user.id,
    #                     account_id=account.id,
    #                     card_id=card_id,
    #                     category_id=category.id,
    #                     description=f"Movimentação para {category.name}",
    #                     value=amount,
    #                     due_day=last_transaction.due_day + timedelta(days=7),
    #                     paid_at=None,
    #                     is_recurring=is_recurring,
    #                     recurring_frequency=recurring_frequency,
    #                     installments=installments,
    #                     current_installment=current_installment,
    #                     parent_id=last_transaction.id,
    #                 )
    #                 transactions.append(transaction)
    #         elif installments:
    #             if current_installment < installments:
    #                 for new_current_installment in range(current_installment + 1, installments + 1):
    #                     last_transaction = transactions[-1]
    #                     print(
    #                         "Transação parcelada: Parcela"
    #                         f" {new_current_installment}/{installments} de {category.name}"
    #                     )
    #                     transaction = Transaction(
    #                         user_id=user.id,
    #                         account_id=account.id,
    #                         card_id=card_id,
    #                         category_id=category.id,
    #                         description=(
    #                             f"Parcela {new_current_installment}/{installments} de"
    #                             f" {category.name}"
    #                         ),
    #                         value=amount,
    #                         due_day=last_transaction.due_day + timedelta(days=30),
    #                         paid_at=None,
    #                         is_recurring=is_recurring,
    #                         recurring_frequency=recurring_frequency,
    #                         installments=installments,
    #                         current_installment=new_current_installment,
    #                         parent_id=last_transaction.id,
    #                     )
    #                     transactions.append(transaction)
    # db.add_all(transactions)
    # db.commit()

    # # Criar orçamentos (budgets) para categorias de despesa
    # today = date.today()
    # budget_month = date(today.year, today.month, 1)
    # budgets_list = []
    # # Orçamento para cada categoria principal de despesa
    # for cat in parent_categories:
    #     if cat.type == "expense":
    #         limit = round(random.uniform(500, 5000), 2)
    #         budget = Budget(
    #             user_id=user.id,
    #             category_id=cat.id,
    #             limit_value=limit,
    #             month=budget_month,
    #         )
    #         budgets_list.append(budget)
    # # Orçamento para cada subcategoria de despesa
    # for cat in subcategories:
    #     if cat.type == "expense":
    #         limit = round(random.uniform(100, 1000), 2)
    #         budget = Budget(
    #             user_id=user.id,
    #             category_id=cat.id,
    #             limit_value=limit,
    #             month=budget_month,
    #         )
    #         budgets_list.append(budget)
    # db.add_all(budgets_list)
    # db.commit()

    print("Fixtures criadas com sucesso!")
