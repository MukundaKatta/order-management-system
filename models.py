from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    items = db.relationship("MenuItem", backref="category", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }


class MenuItem(db.Model):
    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), default="")
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "is_available": self.is_available,
        }


class Table(db.Model):
    __tablename__ = "tables"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False, unique=True)
    capacity = db.Column(db.Integer, nullable=False, default=4)
    status = db.Column(db.String(20), default="available")  # available, occupied, reserved

    orders = db.relationship("Order", backref="table", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "capacity": self.capacity,
            "status": self.status,
        }


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, preparing, ready, served, paid
    total_amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "table_id": self.table_id,
            "table_number": self.table.number if self.table else None,
            "status": self.status,
            "total_amount": self.total_amount,
            "notes": self.notes,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), default="")

    menu_item = db.relationship("MenuItem")

    def to_dict(self):
        return {
            "id": self.id,
            "menu_item_id": self.menu_item_id,
            "menu_item_name": self.menu_item.name if self.menu_item else None,
            "quantity": self.quantity,
            "price": self.price,
            "subtotal": self.quantity * self.price,
            "notes": self.notes,
        }
