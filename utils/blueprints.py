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
from routes.movimentacoes_estoque import movimentos_bp
from routes.movimentacoes_ativos import asset_movements_bp

from routes.admissao import admissao_bp
from routes.ponto48 import ponto48_bp
from routes.pcd import pcd_bp
from routes.rescisoes import termination_bp
from routes.filiais import branch_bp
from routes.controle_faltas import absence_control_bp
from routes.glosas import disallowance_bp, disallowance_files_bp
from routes.estrutura import structure_bp
from routes.importacao_colaboradores import collaborator_import_bp
from routes.updates import updates_bp
from routes.dashboard_pcd import dashboard_pcd_bp
from routes.schedular import schedular_bp
from routes.dashboard_rescisoes import termination_dashboard_bp
from routes.tm_ops import tm_ops_bp
from routes.medidas_disciplinares import disciplinary_measures_bp
from routes.timo import timo_bp
from routes.timo_voice_agents import timo_voice_agents_bp

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
    collaborator_import_bp: "/importacao-colaboradores",
    updates_bp: "/updates",
    termination_dashboard_bp: "/dash/rescisoes",

    #Estoque
    categorias_bp: "/estoque/categorias",
    produtos_bp: "/estoque/produtos",
    movimentos_bp: "/estoque/movimentos",
    asset_movements_bp: "/estoque/movimentos/ativos",

    #Admissão
    admissao_bp: "/admissao/vagas",

    #Rescisões
    termination_bp: "/rescisoes",

    #Indicadores
    pcd_bp: "/pcd",

    #Dashboards PCD
    dashboard_pcd_bp: "/dash/pcd",
    schedular_bp: "/schedular",
    tm_ops_bp: "/tm-ops",
    timo_bp: "/timo",
    timo_voice_agents_bp: "/timo/agentes",

    #Medidas Disciplinares
    disciplinary_measures_bp: "/medidas-disciplinares"
}
