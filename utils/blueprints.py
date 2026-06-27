from routes.supervisores import supervisores_bp
from routes.worksheet import worksheet_bp
from routes.auth import auth_bp
from routes.usuarios import user_bp
from routes.centros import center_bp

blueprints = {
    supervisores_bp: "/supervisores",
    worksheet_bp: "/update",
    auth_bp: "/login",
    user_bp: "/usuarios",
    center_bp: "/centro",
}