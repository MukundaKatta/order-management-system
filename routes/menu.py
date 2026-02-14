from flask import Blueprint, jsonify, request

from models import Category, MenuItem, db

menu_bp = Blueprint("menu", __name__, url_prefix="/api/menu")


# --- Categories ---


@menu_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])


@menu_bp.route("/categories", methods=["POST"])
def create_category():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Category name is required"}), 400

    if Category.query.filter_by(name=data["name"]).first():
        return jsonify({"error": "Category already exists"}), 409

    category = Category(name=data["name"], description=data.get("description", ""))
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@menu_bp.route("/categories/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    category = Category.query.get_or_404(category_id)
    data = request.get_json()

    if data.get("name"):
        category.name = data["name"]
    if "description" in data:
        category.description = data["description"]

    db.session.commit()
    return jsonify(category.to_dict())


@menu_bp.route("/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.items:
        return jsonify({"error": "Cannot delete category with menu items"}), 400
    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category deleted"})


# --- Menu Items ---


@menu_bp.route("/items", methods=["GET"])
def get_items():
    category_id = request.args.get("category_id", type=int)
    available_only = request.args.get("available", "false").lower() == "true"

    query = MenuItem.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if available_only:
        query = query.filter_by(is_available=True)

    items = query.all()
    return jsonify([item.to_dict() for item in items])


@menu_bp.route("/items", methods=["POST"])
def create_item():
    data = request.get_json()
    if not data or not data.get("name") or data.get("price") is None:
        return jsonify({"error": "Name and price are required"}), 400
    if not data.get("category_id"):
        return jsonify({"error": "Category ID is required"}), 400

    category = Category.query.get(data["category_id"])
    if not category:
        return jsonify({"error": "Category not found"}), 404

    item = MenuItem(
        name=data["name"],
        description=data.get("description", ""),
        price=data["price"],
        category_id=data["category_id"],
        is_available=data.get("is_available", True),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@menu_bp.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json()

    if data.get("name"):
        item.name = data["name"]
    if "description" in data:
        item.description = data["description"]
    if data.get("price") is not None:
        item.price = data["price"]
    if data.get("category_id"):
        item.category_id = data["category_id"]
    if "is_available" in data:
        item.is_available = data["is_available"]

    db.session.commit()
    return jsonify(item.to_dict())


@menu_bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Menu item deleted"})
