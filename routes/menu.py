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

    name = data["name"].strip()
    if not name:
        return jsonify({"error": "Category name cannot be empty"}), 400

    if Category.query.filter_by(name=name).first():
        return jsonify({"error": "Category already exists"}), 409

    category = Category(name=name, description=data.get("description", ""))
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@menu_bp.route("/categories/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if data.get("name"):
        name = data["name"].strip()
        if not name:
            return jsonify({"error": "Category name cannot be empty"}), 400
        existing = Category.query.filter_by(name=name).first()
        if existing and existing.id != category.id:
            return jsonify({"error": "Category name already exists"}), 409
        category.name = name
    if "description" in data:
        category.description = data["description"]

    db.session.commit()
    return jsonify(category.to_dict())


@menu_bp.route("/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

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
    search = request.args.get("search", "").strip()

    query = MenuItem.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if available_only:
        query = query.filter_by(is_available=True)
    if search:
        query = query.filter(MenuItem.name.ilike(f"%{search}%"))

    items = query.all()
    return jsonify([item.to_dict() for item in items])


@menu_bp.route("/items", methods=["POST"])
def create_item():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    if not data.get("name") or not data["name"].strip():
        return jsonify({"error": "Name is required"}), 400
    if data.get("price") is None:
        return jsonify({"error": "Price is required"}), 400
    if not isinstance(data["price"], (int, float)) or data["price"] < 0:
        return jsonify({"error": "Price must be a non-negative number"}), 400
    if not data.get("category_id"):
        return jsonify({"error": "Category ID is required"}), 400

    category = Category.query.get(data["category_id"])
    if not category:
        return jsonify({"error": "Category not found"}), 404

    item = MenuItem(
        name=data["name"].strip(),
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
    item = MenuItem.query.get(item_id)
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if data.get("name"):
        name = data["name"].strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        item.name = name
    if "description" in data:
        item.description = data["description"]
    if data.get("price") is not None:
        if not isinstance(data["price"], (int, float)) or data["price"] < 0:
            return jsonify({"error": "Price must be a non-negative number"}), 400
        item.price = data["price"]
    if data.get("category_id"):
        category = Category.query.get(data["category_id"])
        if not category:
            return jsonify({"error": "Category not found"}), 404
        item.category_id = data["category_id"]
    if "is_available" in data:
        if not isinstance(data["is_available"], bool):
            return jsonify({"error": "is_available must be a boolean"}), 400
        item.is_available = data["is_available"]

    db.session.commit()
    return jsonify(item.to_dict())


@menu_bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = MenuItem.query.get(item_id)
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Menu item deleted"})


@menu_bp.route("/items/<int:item_id>/toggle", methods=["PATCH"])
def toggle_item_availability(item_id):
    item = MenuItem.query.get(item_id)
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    item.is_available = not item.is_available
    db.session.commit()
    return jsonify(item.to_dict())
