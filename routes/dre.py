# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.dre import DreService


dre_bp = Blueprint("Controle DRE", __name__)
service = DreService()


@dre_bp.get("")
def read():
    return service.read()


@dre_bp.post("/importar/previa")
def preview_import():
    return service.preview_import()


@dre_bp.post("/importar")
def import_source():
    return service.import_source()


@dre_bp.post("/beneficios/gerar")
def generate_current_benefits():
    return service.generate_current_benefits()


@dre_bp.post("/manual")
def create_manual_entry():
    return service.create_manual_entry()


@dre_bp.delete("/competencias/<competencia>")
def delete_competence(competencia):
    return service.delete_competence(competencia=competencia)
