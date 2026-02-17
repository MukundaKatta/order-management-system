from flask import Blueprint, jsonify, request

from models import Order, Table, db

tables_bp = Blueprint("tables", __name__, url_prefix="/api/tables")

VALID_STATUSES = ["available", "occupied", "reserved"]


@tables_bp.route("", methods=["GET"])
def get_tables():
    status = request.args.get("status")
    query = Table.query.order_by(Table.number)

    if status:
        if status not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}), 400
        query = query.filter_by(status=status)

    tables = query.all()
    return jsonify([t.to_dict() for t in tables])


@tables_bp.route("/floor", methods=["GET"])
def get_floor_map():
    """Return all tables with their current active order info for floor map view.

    Each table includes a summary of its current (non-paid) orders so the
    floor staff can see at a glance which tables are active and what they owe.
    """
    tables = Table.query.order_by(Table.number).all()
    result = []

    for table in tables:
        active_orders = (
            Order.query.filter(
                Order.table_id == table.id,
                Order.status != "paid",
            )
            .order_by(Order.created_at.asc())
            .all()
        )

        table_data = table.to_dict()
        table_data["active_orders"] = [
            {
                "id": order.id,
                "status": order.status,
                "total_amount": order.total_amount,
                "item_count": sum(item.quantity for item in order.items),
                "created_at": order.created_at.isoformat() if order.created_at else None,
            }
            for order in active_orders
        ]
        table_data["total_active_amount"] = round(
            sum(o.total_amount or 0 for o in active_orders), 2
        )

        result.append(table_data)

    return jsonify(result)


@tables_bp.route("", methods=["POST"])
def create_table():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    if not data.get("number"):
        return jsonify({"error": "Table number is required"}), 400
    if not isinstance(data["number"], int) or data["number"] < 1:
        return jsonify({"error": "Table number must be a positive integer"}), 400

    if Table.query.filter_by(number=data["number"]).first():
        return jsonify({"error": "Table number already exists"}), 409

    capacity = data.get("capacity", 4)
    if not isinstance(capacity, int) or capacity < 1:
        return jsonify({"error": "Capacity must be a positive integer"}), 400

    table = Table(
        number=data["number"],
        capacity=capacity,
    )
    db.session.add(table)
    db.session.commit()
    return jsonify(table.to_dict()), 201


@tables_bp.route("/<int:table_id>", methods=["PUT"])
def update_table(table_id):
    table = Table.query.get(table_id)
    if not table:
        return jsonify({"error": "Table not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if data.get("number"):
        if not isinstance(data["number"], int) or data["number"] < 1:
            return jsonify({"error": "Table number must be a positive integer"}), 400
        existing = Table.query.filter_by(number=data["number"]).first()
        if existing and existing.id != table.id:
            return jsonify({"error": "Table number already exists"}), 409
        table.number = data["number"]

    if data.get("capacity"):
        if not isinstance(data["capacity"], int) or data["capacity"] < 1:
            return jsonify({"error": "Capacity must be a positive integer"}), 400
        table.capacity = data["capacity"]

    if data.get("status"):
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}), 400
        table.status = data["status"]

    db.session.commit()
    return jsonify(table.to_dict())


@tables_bp.route("/<int:table_id>", methods=["DELETE"])
def delete_table(table_id):
    table = Table.query.get(table_id)
    if not table:
        return jsonify({"error": "Table not found"}), 404

    if table.status == "occupied":
        return jsonify({"error": "Cannot delete an occupied table"}), 400
    db.session.delete(table)
    db.session.commit()
    return jsonify({"message": "Table deleted"})
