# Rotas HTTP de planilhas.
# Dependências externas.
from flask import request, Blueprint
# Módulos internos da aplicação.
from services.worksheet import WorkSheet

worksheet_bp = Blueprint("WorkSheet", __name__)
service = WorkSheet()

@worksheet_bp.route("/funcionarios", methods=["POST"])
def funcionarios(): return service.__updateEmployees__()

@worksheet_bp.route("/centroDeCusto", methods=["POST"])
def centro_de_custo(): return service.__updateCosts__()

@worksheet_bp.route("/supervisores", methods=["POST"])
def supervisores(): return service.__updateSupervisors__()
