from flask import Blueprint, jsonify, request

from models import MenuItem, Order, OrderItem, Table, db

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("", methods=["GET"])
def get_orders():
    status = request.args.get("status")
    table_id = request.args.get("table_id", type=int)

    query = Order.query
    if status:
        query = query.filter_by(status=status)
    if table_id:
        query = query.filter_by(table_id=table_id)

    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@orders_bp.route("/<int:order_id>", methods=["GET"])
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict())


@orders_bp.route("", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data or not data.get("table_id"):
        return jsonify({"error": "Table ID is required"}), 400
    if not data.get("items") or len(data["items"]) == 0:
        return jsonify({"error": "At least one item is required"}), 400

    table = Table.query.get(data["table_id"])
    if not table:
        return jsonify({"error": "Table not found"}), 404

    order = Order(
        table_id=data["table_id"],
        notes=data.get("notes", ""),
    )
    db.session.add(order)

    total = 0.0
    for item_data in data["items"]:
        menu_item = MenuItem.query.get(item_data.get("menu_item_id"))
        if not menu_item:
            db.session.rollback()
            return jsonify({"error": f"Menu item {item_data.get('menu_item_id')} not found"}), 404
        if not menu_item.is_available:
            db.session.rollback()
            return jsonify({"error": f"'{menu_item.name}' is currently unavailable"}), 400

        quantity = item_data.get("quantity", 1)
        order_item = OrderItem(
            order=order,
            menu_item_id=menu_item.id,
            quantity=quantity,
            price=menu_item.price,
            notes=item_data.get("notes", ""),
        )
        db.session.add(order_item)
        total += menu_item.price * quantity

    order.total_amount = round(total, 2)

    # Mark table as occupied
    table.status = "occupied"

    db.session.commit()
    return jsonify(order.to_dict()), 201


@orders_bp.route("/<int:order_id>", methods=["PUT"])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json()

    valid_statuses = ["pending", "preparing", "ready", "served", "paid"]
    new_status = data.get("status")

    if new_status and new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400

    if new_status:
        order.status = new_status

    if "notes" in data:
        order.notes = data["notes"]

    # Free up table when order is paid
    if new_status == "paid":
        active_orders = Order.query.filter(
            Order.table_id == order.table_id,
            Order.status != "paid",
            Order.id != order.id,
        ).count()
        if active_orders == 0:
            order.table.status = "available"

    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.route("/<int:order_id>", methods=["DELETE"])
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status in ("served", "paid"):
        return jsonify({"error": "Cannot cancel a served or paid order"}), 400

    table = order.table
    db.session.delete(order)

    # Free table if no other active orders
    active_orders = Order.query.filter(
        Order.table_id == table.id,
        Order.status != "paid",
        Order.id != order_id,
    ).count()
    if active_orders == 0:
        table.status = "available"

    db.session.commit()
    return jsonify({"message": "Order cancelled"})
