from flask import Blueprint

from services.timo_voice_agents import TimoVoiceAgentService


timo_voice_agents_bp = Blueprint("TimoVoiceAgents", __name__)
service = TimoVoiceAgentService()


@timo_voice_agents_bp.get("")
def list_agents():
    return service.list()


@timo_voice_agents_bp.get("/tema")
def agent_theme():
    return service.agent_theme()


@timo_voice_agents_bp.post("/pareamentos")
def create_pairing():
    return service.create_pairing()


@timo_voice_agents_bp.post("/parear")
def pair_agent():
    return service.pair()


@timo_voice_agents_bp.patch("/<string:agent_id>/controle")
def control_agent(agent_id):
    return service.control(agent_id=agent_id)


@timo_voice_agents_bp.patch("/<string:agent_id>/selecionar")
def select_agent(agent_id):
    return service.select(agent_id=agent_id)


@timo_voice_agents_bp.delete("/<string:agent_id>")
def revoke_agent(agent_id):
    return service.revoke(agent_id=agent_id)
