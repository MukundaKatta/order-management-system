"""Seed script to populate the database with sample data."""

from app import create_app
from models import Category, MenuItem, Table, db


def seed():
    app = create_app()
    with app.app_context():
        # Skip if data already exists
        if Category.query.first():
            print("Database already has data. Skipping seed.")
            return

        # Categories
        appetizers = Category(name="Appetizers", description="Start your meal right")
        mains = Category(name="Main Course", description="Hearty entrees")
        desserts = Category(name="Desserts", description="Sweet endings")
        drinks = Category(name="Beverages", description="Refreshing drinks")
        db.session.add_all([appetizers, mains, desserts, drinks])
        db.session.flush()

        # Menu Items
        items = [
            MenuItem(name="Spring Rolls", description="Crispy vegetable spring rolls", price=6.99, category_id=appetizers.id),
            MenuItem(name="Garlic Bread", description="Toasted bread with garlic butter", price=4.99, category_id=appetizers.id),
            MenuItem(name="Soup of the Day", description="Ask your server for today's selection", price=5.99, category_id=appetizers.id),
            MenuItem(name="Grilled Salmon", description="Atlantic salmon with lemon butter sauce", price=18.99, category_id=mains.id),
            MenuItem(name="Chicken Parmesan", description="Breaded chicken with marinara and mozzarella", price=15.99, category_id=mains.id),
            MenuItem(name="Beef Burger", description="Angus beef patty with fries", price=13.99, category_id=mains.id),
            MenuItem(name="Pasta Primavera", description="Penne with seasonal vegetables", price=12.99, category_id=mains.id),
            MenuItem(name="Chocolate Cake", description="Rich chocolate layer cake", price=7.99, category_id=desserts.id),
            MenuItem(name="Cheesecake", description="New York style cheesecake", price=8.99, category_id=desserts.id),
            MenuItem(name="Ice Cream", description="Three scoops, choice of flavor", price=5.99, category_id=desserts.id),
            MenuItem(name="Coffee", description="Freshly brewed", price=2.99, category_id=drinks.id),
            MenuItem(name="Iced Tea", description="House-made iced tea", price=2.49, category_id=drinks.id),
            MenuItem(name="Fresh Juice", description="Orange or apple juice", price=3.99, category_id=drinks.id),
            MenuItem(name="Soda", description="Coke, Sprite, or Fanta", price=1.99, category_id=drinks.id),
        ]
        db.session.add_all(items)

        # Tables
        tables = [
            Table(number=1, capacity=2),
            Table(number=2, capacity=2),
            Table(number=3, capacity=4),
            Table(number=4, capacity=4),
            Table(number=5, capacity=6),
            Table(number=6, capacity=6),
            Table(number=7, capacity=8),
            Table(number=8, capacity=4),
        ]
        db.session.add_all(tables)

        db.session.commit()
        print("Database seeded successfully!")
        print(f"  - {len([appetizers, mains, desserts, drinks])} categories")
        print(f"  - {len(items)} menu items")
        print(f"  - {len(tables)} tables")


if __name__ == "__main__":
    seed()
