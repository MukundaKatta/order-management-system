from flask import Flask, render_template

from config import Config
from models import db
from routes.menu import menu_bp
from routes.orders import orders_bp
from routes.tables import tables_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Register API blueprints
    app.register_blueprint(menu_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(tables_bp)

    # Page routes
    @app.route("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/tables")
    def tables_page():
        return render_template("tables.html")

    @app.route("/menu")
    def menu_page():
        return render_template("menu.html")

    @app.route("/orders")
    def orders_page():
        return render_template("orders.html")

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
