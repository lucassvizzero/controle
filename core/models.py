from sqlalchemy import DECIMAL, Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base
from core.schemas import BankName, BrandName, CategoryType


# 🔹 Usuário
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True)
    username = Column(String(50), unique=True)
    password = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relacionamentos
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


# 🔹 Contas Bancárias
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100))
    bank = Column(Enum(BankName, name="bank_name"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relacionamentos
    user = relationship("User", back_populates="accounts")
    cards = relationship("Card", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )


# 🔹 Cartões de Crédito
class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    name = Column(String(100))
    brand = Column(Enum(BrandName, name="brand_name"))
    due_day = Column(Integer, nullable=False)
    close_day = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relacionamentos
    user = relationship("User", back_populates="cards")
    account = relationship("Account", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card", cascade="all, delete-orphan")


# 🔹 Categorias de Transações
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100))
    type = Column(Enum(CategoryType, name="category_type"))
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    system_category = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relacionamentos
    user = relationship("User", back_populates="categories")
    parent = relationship("Category", remote_side=[id], back_populates="subcategories")
    subcategories = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    # Relacionamento com transações e orçamentos
    transactions = relationship(
        "Transaction", back_populates="category", cascade="all, delete-orphan"
    )
    budgets = relationship("Budget", back_populates="category", cascade="all, delete-orphan")


# 🔹 Orçamentos
class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    limit_value = Column(DECIMAL(15, 2), nullable=False)
    month = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relacionamentos
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")


# 🔹 Transações
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    description = Column(String, nullable=True)
    value = Column(DECIMAL(15, 2), nullable=False)
    due_at = Column(Date, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    is_recurring = Column(Boolean, default=False)
    recurring_frequency = Column(
        Enum("mensal", "semanal", "anual", name="frequency_type"), nullable=True
    )
    recurring_end_date = Column(Date, nullable=True)
    installments = Column(Integer, nullable=True)
    current_installment = Column(Integer, nullable=True)

    # Relacionamentos
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    card = relationship("Card", back_populates="transactions")
    parent = relationship("Transaction", remote_side=[id], back_populates="linked_transactions")
    linked_transactions = relationship(
        "Transaction", back_populates="parent", cascade="all, delete-orphan"
    )
