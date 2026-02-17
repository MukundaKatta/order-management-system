from datetime import datetime, time, timezone

from flask import Blueprint, jsonify
from sqlalchemy import func

from models import MenuItem, Order, OrderItem, db

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def _today_range():
    """Return the start and end datetimes for today (UTC)."""
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = datetime.combine(today, time.max, tzinfo=timezone.utc)
    return start, end


@reports_bp.route("/summary", methods=["GET"])
def daily_summary():
    """Return today's summary: total orders, revenue, average order value,
    and the top 5 most popular items.
    """
    start, end = _today_range()

    # All orders created today
    today_orders = Order.query.filter(
        Order.created_at >= start,
        Order.created_at <= end,
    )

    total_orders = today_orders.count()

    # Revenue comes only from paid orders
    paid_orders = today_orders.filter(Order.status == "paid")
    revenue_result = paid_orders.with_entities(func.sum(Order.total_amount)).scalar()
    revenue = round(revenue_result or 0, 2)

    avg_order_value = round(revenue / total_orders, 2) if total_orders > 0 else 0

    # Popular items today (across all order statuses)
    popular_items = (
        db.session.query(
            MenuItem.id,
            MenuItem.name,
            func.sum(OrderItem.quantity).label("total_ordered"),
        )
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.created_at >= start, Order.created_at <= end)
        .group_by(MenuItem.id, MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    return jsonify({
        "date": datetime.now(timezone.utc).date().isoformat(),
        "total_orders": total_orders,
        "revenue": revenue,
        "avg_order_value": avg_order_value,
        "popular_items": [
            {
                "id": item.id,
                "name": item.name,
                "total_ordered": int(item.total_ordered),
            }
            for item in popular_items
        ],
    })


@reports_bp.route("/popular-items", methods=["GET"])
def popular_items():
    """Return the top 10 most ordered menu items with total counts (all time)."""
    results = (
        db.session.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.category_id,
            func.sum(OrderItem.quantity).label("total_ordered"),
            func.count(OrderItem.order_id.distinct()).label("order_count"),
        )
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .group_by(MenuItem.id, MenuItem.name, MenuItem.price, MenuItem.category_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
        .all()
    )

    return jsonify([
        {
            "id": row.id,
            "name": row.name,
            "price": row.price,
            "category_id": row.category_id,
            "total_ordered": int(row.total_ordered),
            "order_count": int(row.order_count),
        }
        for row in results
    ])
