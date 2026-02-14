from flask import Blueprint, jsonify, request

from models import Table, db

tables_bp = Blueprint("tables", __name__, url_prefix="/api/tables")


@tables_bp.route("", methods=["GET"])
def get_tables():
    status = request.args.get("status")
    query = Table.query.order_by(Table.number)
    if status:
        query = query.filter_by(status=status)
    tables = query.all()
    return jsonify([t.to_dict() for t in tables])


@tables_bp.route("", methods=["POST"])
def create_table():
    data = request.get_json()
    if not data or not data.get("number"):
        return jsonify({"error": "Table number is required"}), 400

    if Table.query.filter_by(number=data["number"]).first():
        return jsonify({"error": "Table number already exists"}), 409

    table = Table(
        number=data["number"],
        capacity=data.get("capacity", 4),
    )
    db.session.add(table)
    db.session.commit()
    return jsonify(table.to_dict()), 201


@tables_bp.route("/<int:table_id>", methods=["PUT"])
def update_table(table_id):
    table = Table.query.get_or_404(table_id)
    data = request.get_json()

    if data.get("number"):
        existing = Table.query.filter_by(number=data["number"]).first()
        if existing and existing.id != table.id:
            return jsonify({"error": "Table number already exists"}), 409
        table.number = data["number"]

    if data.get("capacity"):
        table.capacity = data["capacity"]

    valid_statuses = ["available", "occupied", "reserved"]
    if data.get("status"):
        if data["status"] not in valid_statuses:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
        table.status = data["status"]

    db.session.commit()
    return jsonify(table.to_dict())


@tables_bp.route("/<int:table_id>", methods=["DELETE"])
def delete_table(table_id):
    table = Table.query.get_or_404(table_id)
    if table.status == "occupied":
        return jsonify({"error": "Cannot delete an occupied table"}), 400
    db.session.delete(table)
    db.session.commit()
    return jsonify({"message": "Table deleted"})
