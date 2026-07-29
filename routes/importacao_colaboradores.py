from flask import Blueprint

from services.importacao_colaboradores import CollaboratorImportService


collaborator_import_bp = Blueprint("Importação de Colaboradores", __name__)
service = CollaboratorImportService()


@collaborator_import_bp.post("")
def create_import():
    return service.create()


@collaborator_import_bp.get("/<string:job_id>")
def import_status(job_id):
    return service.read(job_id)
