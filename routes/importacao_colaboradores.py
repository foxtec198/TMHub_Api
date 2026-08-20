# Rotas HTTP de importação de colaboradores.
# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.importacao_colaboradores import CollaboratorImportService


collaborator_import_bp = Blueprint("Importação de Colaboradores", __name__)
service = CollaboratorImportService()


@collaborator_import_bp.get("/empresas")
def companies():
    return service.companies()


@collaborator_import_bp.post("")
def create_import():
    return service.create()


@collaborator_import_bp.post("/upload/iniciar")
def start_import_upload():
    return service.start_upload()


@collaborator_import_bp.post("/<string:job_id>/parte")
def upload_import_chunk(job_id):
    return service.upload_chunk(job_id)


@collaborator_import_bp.post("/<string:job_id>/concluir")
def complete_import_upload(job_id):
    return service.complete_upload(job_id)


@collaborator_import_bp.get("/<string:job_id>")
def import_status(job_id):
    return service.read(job_id)
