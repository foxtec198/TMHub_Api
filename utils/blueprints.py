from routes.supervisores import supervisores_bp
from routes.worksheet import worksheet_bp
from routes.auth import auth_bp
from routes.usuarios import user_bp
from routes.centros import center_bp
from routes.funcionarios import funcionarios_bp
from routes.reposicao import replace_bp
from routes.dashboard import dashboards_bp
from routes.rpa import rpa_bp
from routes.reservas_tecnicas import floaters_bp

from routes.projects import project_bp

from routes.categorias import categorias_bp
from routes.produtos import produtos_bp
from routes.movimentos import movimentos_bp

from routes.admissao import admissao_bp
from routes.ponto48 import ponto48_bp
from routes.pcd import pcd_bp
from routes.filiais import branch_bp
from routes.controle_faltas import absence_control_bp
from routes.glosas import disallowance_bp, disallowance_files_bp
from routes.estrutura import structure_bp

blueprints = {
    rpa_bp: "/rpa",
    auth_bp: "/login",
    replace_bp: "/repo",
    user_bp: "/usuarios",
    worksheet_bp: "/update",
    center_bp: "/centro",
    supervisores_bp: "/supervisores",
    funcionarios_bp: "/funcionarios",
    floaters_bp: "/reservas",
    project_bp: "/projetos",

    # Dashboards
    dashboards_bp: "/dash",
    ponto48_bp: "/dash/ponto-48h",
    branch_bp: "/filiais",
    absence_control_bp: "/controle-faltas",
    disallowance_bp: "/glosas",
    disallowance_files_bp: "/arquivos/glosas",
    structure_bp: "/estrutura",

    #Estoque
    categorias_bp: "/estoque/categorias",
    produtos_bp: "/estoque/produtos",
    movimentos_bp: "/estoque/movimentos",

    #Admissão
    admissao_bp: "/admissao/vagas",

    #Indicadores
    pcd_bp: "/pcd",
}
