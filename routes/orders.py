from flask import Blueprint, jsonify, request

from models import MenuItem, Order, OrderItem, Table, db

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

# Valid status transitions: current_status -> set of allowed next statuses
VALID_STATUS_TRANSITIONS = {
    "pending": {"preparing", "paid"},
    "preparing": {"ready"},
    "ready": {"served"},
    "served": {"paid"},
    "paid": set(),
}

VALID_STATUSES = list(VALID_STATUS_TRANSITIONS.keys())


def _validate_status_transition(current_status, new_status):
    """Check whether a status transition is allowed.

    Returns an error message string if invalid, or None if valid.
    """
    if new_status not in VALID_STATUSES:
        return f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"

    allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        return (
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions from '{current_status}': "
            f"{', '.join(sorted(allowed)) if allowed else 'none (terminal state)'}"
        )

    return None


def _free_table_if_no_active_orders(table, exclude_order_id=None):
    """Set the table to 'available' if it has no remaining non-paid orders."""
    query = Order.query.filter(
        Order.table_id == table.id,
        Order.status != "paid",
    )
    if exclude_order_id is not None:
        query = query.filter(Order.id != exclude_order_id)

    if query.count() == 0:
        table.status = "available"


@orders_bp.route("", methods=["GET"])
def get_orders():
    status = request.args.get("status")
    table_id = request.args.get("table_id", type=int)

    query = Order.query
    if status:
        if status not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status filter. Must be one of: {', '.join(VALID_STATUSES)}"}), 400
        query = query.filter_by(status=status)
    if table_id:
        query = query.filter_by(table_id=table_id)

    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@orders_bp.route("/active", methods=["GET"])
def get_active_orders():
    """Return all orders that are not yet paid."""
    orders = (
        Order.query.filter(Order.status != "paid")
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify([o.to_dict() for o in orders])


@orders_bp.route("/kitchen", methods=["GET"])
def get_kitchen_orders():
    """Return pending and preparing orders grouped for the kitchen display.

    Orders are sorted oldest-first so the kitchen processes them in FIFO order.
    """
    orders = (
        Order.query.filter(Order.status.in_(["pending", "preparing"]))
        .order_by(Order.created_at.asc())
        .all()
    )

    grouped = {"pending": [], "preparing": []}
    for order in orders:
        grouped[order.status].append(order.to_dict())

    return jsonify(grouped)


@orders_bp.route("/<int:order_id>", methods=["GET"])
def get_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order.to_dict())


@orders_bp.route("", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    if not data.get("table_id"):
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
        menu_item_id = item_data.get("menu_item_id")
        menu_item = MenuItem.query.get(menu_item_id) if menu_item_id else None
        if not menu_item:
            db.session.rollback()
            return jsonify({"error": f"Menu item {menu_item_id} not found"}), 404
        if not menu_item.is_available:
            db.session.rollback()
            return jsonify({"error": f"'{menu_item.name}' is currently unavailable"}), 400

        quantity = item_data.get("quantity", 1)
        if not isinstance(quantity, int) or quantity < 1:
            db.session.rollback()
            return jsonify({"error": "Quantity must be a positive integer"}), 400

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
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    new_status = data.get("status")

    if new_status:
        error = _validate_status_transition(order.status, new_status)
        if error:
            return jsonify({"error": error}), 400
        order.status = new_status

    if "notes" in data:
        order.notes = data["notes"]

    # Free up table when order is paid
    if new_status == "paid":
        _free_table_if_no_active_orders(order.table, exclude_order_id=order.id)

    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.route("/<int:order_id>/items", methods=["POST"])
def add_items_to_order(order_id):
    """Add one or more items to an existing order.

    The order must not be in a terminal state (paid).
    """
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    if order.status == "paid":
        return jsonify({"error": "Cannot add items to a paid order"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    items_data = data.get("items", [])
    if not items_data or len(items_data) == 0:
        return jsonify({"error": "At least one item is required"}), 400

    added_total = 0.0
    for item_data in items_data:
        menu_item_id = item_data.get("menu_item_id")
        menu_item = MenuItem.query.get(menu_item_id) if menu_item_id else None
        if not menu_item:
            db.session.rollback()
            return jsonify({"error": f"Menu item {menu_item_id} not found"}), 404
        if not menu_item.is_available:
            db.session.rollback()
            return jsonify({"error": f"'{menu_item.name}' is currently unavailable"}), 400

        quantity = item_data.get("quantity", 1)
        if not isinstance(quantity, int) or quantity < 1:
            db.session.rollback()
            return jsonify({"error": "Quantity must be a positive integer"}), 400

        order_item = OrderItem(
            order=order,
            menu_item_id=menu_item.id,
            quantity=quantity,
            price=menu_item.price,
            notes=item_data.get("notes", ""),
        )
        db.session.add(order_item)
        added_total += menu_item.price * quantity

    order.total_amount = round((order.total_amount or 0) + added_total, 2)

    db.session.commit()
    return jsonify(order.to_dict()), 201


@orders_bp.route("/<int:order_id>", methods=["DELETE"])
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    if order.status in ("served", "paid"):
        return jsonify({"error": "Cannot cancel a served or paid order"}), 400

    table = order.table
    db.session.delete(order)

    # Free table if no other active orders
    _free_table_if_no_active_orders(table, exclude_order_id=order_id)

    db.session.commit()
    return jsonify({"message": "Order cancelled"})
