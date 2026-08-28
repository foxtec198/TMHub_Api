# Rotas HTTP de centros de custo.
# Dependências externas.
from flask import request, Blueprint
# Módulos internos da aplicação.
from services.centros import CostsCenterService

center_bp = Blueprint("Centros de Custo", __name__)
service = CostsCenterService()


@center_bp.get("/empresas")
def companies():
    return service.companies()


@center_bp.post("/importar")
def import_centers():
    return service.import_centers()


@center_bp.post("/dados")
def sync_centers_from_data():
    return service.sync_from_data()


@center_bp.get("/importacoes/<string:job_id>")
def center_import_status(job_id):
    return service.import_status(job_id)

# Encaminha a requisição para o fluxo principal do módulo.
@center_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
        case "PATCH": response = service.update()
        case "DELETE": response = service.delete()
    return response


@center_bp.route("/configuracoes", methods=["GET", "PATCH"])
def settings():
    if request.method == "GET":
        return service.settings()
    return service.update_settings()
