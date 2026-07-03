from routes.supervisores import supervisores_bp
from routes.worksheet import worksheet_bp
from routes.auth import auth_bp
from routes.usuarios import user_bp
from routes.centros import center_bp
from routes.funcionarios import funcionarios_bp
from routes.reposicao import replace_bp
from routes.categorias import categorias_bp 
from routes.produtos import produtos_bp
from routes.movimentos import movimentos_bp

blueprints = {
    supervisores_bp: "/supervisores",
    funcionarios_bp: "/funcionarios",
    worksheet_bp: "/update",
    auth_bp: "/login",
    user_bp: "/usuarios",
    center_bp: "/centro",
    replace_bp: "/repo",

    #Estoque 

    categorias_bp: "/estoque/categorias",
    produtos_bp: "/estoque/produtos",
    movimentos_bp: "/estoque/movimentos",
}