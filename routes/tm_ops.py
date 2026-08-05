from flask import Blueprint, request

from services.tm_ops import TMOpsService


tm_ops_bp = Blueprint("TMOps", __name__)
service = TMOpsService()


@tm_ops_bp.post("/login")
def login(): return service.login()


@tm_ops_bp.get("/sessao")
def session(): return service.session()


@tm_ops_bp.route("/acessos", methods=["GET", "POST"])
def accesses():
    return service.read_accesses() if request.method == "GET" else service.provision_access()


@tm_ops_bp.get("/acessos/<int:employee_id>")
def access_detail(employee_id): return service.read_access_detail(employee_id)


@tm_ops_bp.route("/rotinas", methods=["GET", "POST"])
def routines(): return service.read_routines() if request.method == "GET" else service.create_routine()


@tm_ops_bp.route("/rotinas/<int:routine_id>", methods=["PATCH", "DELETE"])
def routine_by_id(routine_id):
    return service.update_routine(routine_id) if request.method == "PATCH" else service.delete_routine(routine_id)


@tm_ops_bp.route("/rotinas/<int:routine_id>/vinculos", methods=["GET", "POST"])
def routine_links(routine_id): return service.routine_links(routine_id)


@tm_ops_bp.delete("/rotinas/<int:routine_id>/vinculos/<int:link_id>")
def remove_routine_link(routine_id, link_id): return service.remove_routine_link(routine_id, link_id)


@tm_ops_bp.post("/rotinas/processar")
def process_routines(): return service.process_routines()


@tm_ops_bp.get("/tarefas")
def tasks(): return service.read_tasks()


@tm_ops_bp.get("/tarefas/<int:task_id>")
def task_detail(task_id): return service.read_task(task_id)


@tm_ops_bp.get("/tarefas/minhas")
def my_tasks(): return service.read_my_tasks()


@tm_ops_bp.post("/tarefas/<int:task_id>/acao")
def task_action(task_id): return service.action_task(task_id)


@tm_ops_bp.post("/tarefas/<int:task_id>/geolocalizacoes")
def task_geolocations(task_id): return service.save_task_geolocation(task_id)


@tm_ops_bp.post("/tarefas/<int:task_id>/respostas")
def task_answers(task_id): return service.save_task_answers(task_id)


@tm_ops_bp.post("/tarefas/<int:task_id>/respostas/<int:item_id>/evidencias")
def task_evidence(task_id, item_id): return service.save_task_evidence(task_id, item_id)


@tm_ops_bp.get("/evidencias/<int:evidence_id>/arquivo")
def task_evidence_file(evidence_id): return service.serve_task_evidence(evidence_id)


@tm_ops_bp.route("/checklists", methods=["GET", "POST"])
def checklists(): return service.read_checklists() if request.method == "GET" else service.create_checklist()


@tm_ops_bp.route("/checklists/<int:checklist_id>", methods=["PATCH", "DELETE"])
def checklist_by_id(checklist_id):
    return service.update_checklist(checklist_id) if request.method == "PATCH" else service.delete_checklist(checklist_id)
