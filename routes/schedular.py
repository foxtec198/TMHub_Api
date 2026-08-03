from flask import Blueprint, request

from services.schedular import SchedularService


schedular_bp = Blueprint("Schedular", __name__)
service = SchedularService()


@schedular_bp.post("/login")
def login():
    return service.login()


@schedular_bp.get("/sessao")
def session():
    return service.session()


@schedular_bp.route("/acessos", methods=["GET", "POST"])
def provision_access():
    return service.read_accesses() if request.method == "GET" else service.provision_access()


@schedular_bp.route("/rotinas", methods=["GET", "POST"])
def routines():
    return service.read_routines() if request.method == "GET" else service.create_routine()


@schedular_bp.route("/rotinas/<int:routine_id>", methods=["PATCH", "DELETE"])
def routine_by_id(routine_id):
    return service.update_routine(routine_id) if request.method == "PATCH" else service.delete_routine(routine_id)


@schedular_bp.route("/rotinas/<int:routine_id>/vinculos", methods=["GET", "POST"])
def routine_links(routine_id):
    return service.routine_links(routine_id)


@schedular_bp.delete("/rotinas/<int:routine_id>/vinculos/<int:link_id>")
def remove_routine_link(routine_id, link_id):
    return service.remove_routine_link(routine_id, link_id)


@schedular_bp.post("/rotinas/processar")
def process_routines():
    return service.process_routines()


@schedular_bp.get("/tarefas")
def tasks():
    return service.read_tasks()


@schedular_bp.get("/tarefas/minhas")
def my_tasks():
    return service.read_my_tasks()


@schedular_bp.post("/tarefas/<int:task_id>/acao")
def task_action(task_id):
    return service.action_task(task_id)


@schedular_bp.post("/tarefas/<int:task_id>/geolocalizacoes")
def task_geolocations(task_id):
    return service.save_task_geolocation(task_id)


@schedular_bp.post("/tarefas/<int:task_id>/respostas")
def task_answers(task_id):
    return service.save_task_answers(task_id)


@schedular_bp.post("/tarefas/<int:task_id>/respostas/<int:item_id>/evidencias")
def task_evidence(task_id, item_id):
    return service.save_task_evidence(task_id, item_id)


@schedular_bp.get("/evidencias/<int:evidence_id>/arquivo")
def task_evidence_file(evidence_id):
    return service.serve_task_evidence(evidence_id)


@schedular_bp.route("/checklists", methods=["GET", "POST"])
def checklists():
    return service.read_checklists() if request.method == "GET" else service.create_checklist()


@schedular_bp.route("/checklists/<int:checklist_id>", methods=["PATCH", "DELETE"])
def checklist_by_id(checklist_id):
    return service.update_checklist(checklist_id) if request.method == "PATCH" else service.delete_checklist(checklist_id)
