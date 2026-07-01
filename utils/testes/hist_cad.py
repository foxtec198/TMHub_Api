from sqlalchemy import create_engine, text
from utils.testes.historico_output import historico
from rapidfuzz import process, fuzz
from datetime import datetime as dt
from dotenv import load_dotenv
from os import getenv
import unicodedata

def remove_acentos(texto):
    if texto is None:
        return None
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

load_dotenv();

with create_engine(getenv("DB_URI")).connect() as conn:
    # Colaboradores
    colaboradores = conn.execute(text("SELECT c.id, c.nome, c.centro_id, cc.local FROM colaboradores c join centro_de_custo cc on cc.id = c.centro_id")).fetchall()
    nomes_colab = {row[1]: row[0] for row in colaboradores}
    nomes_locais = {row[3]: row[2] for row in colaboradores}

    def match_colaborador(nome_sujo, threshold=95):
        nome_sujo = nome_sujo.upper().strip()
        resultado = process.extractOne(nome_sujo, nomes_colab.keys(), scorer=fuzz.token_sort_ratio)
        if resultado and resultado[1] >= threshold:
            nome_match, score, _ = resultado
            return nomes_colab[nome_match], nome_match, score
        return 0, None, 0

    def match_local(local_sujo, threshold=85):
        local_sujo = local_sujo.upper().strip()
        resultado = process.extractOne(local_sujo, nomes_locais.keys(), scorer=fuzz.token_sort_ratio)
        if resultado and resultado[1] >= threshold:
            nome_match, score, _ = resultado
            return nomes_colab[nome_match], nome_match, score
        return 0, None, 0

    for item in historico:
        dia, mes = item.get("data").split("/")
        data = dt.now().replace(day=int(dia), month=int(mes))

        local = remove_acentos(str(item.get("local")))
        ausente = remove_acentos(str(item.get("ausente")))
        reserva = remove_acentos(str(item.get("reserva")))
        motivo = remove_acentos(str(item.get("motivo")))
        obs = remove_acentos(str(item.get("obs")))

        status = "approve"
        requisicao_id = 0

        ausente_id, ausente_nome, score_ausente = match_colaborador(ausente)
        local_id, nome_local, score_local = match_local(local)
        
        reserva_id, nome_reserva, score_reserva = match_colaborador(reserva)

        outMatch = False
        if local_id == 0 and not nome_local: 
            local = conn.execute(text(f"select cc.id, cc.local from colaboradores c join centro_de_custo cc on cc.id = c.centro_id where c.id = {ausente_id}")).first()
            print(ausente_id, ausente)
            
            local_id, nome_local = local
            outMatch = True
            
        print(local_id, nome_local, "Fora do match: ", outMatch)
        print("="*50)
        print(f"Cadastrando Historico - {ausente}")

        conn.execute(
            text(
                f"""INSERT INTO rp_historico(requisicao_id, reserva_id, ausente_id, cc, created_at, ended_at, status, obs, motivo)
                VALUES({requisicao_id}, {reserva_id}, {ausente_id}, {local_id}, '{data}', '{data}', '{status}', '{obs}', '{motivo}')"""
            )
        );
    conn.commit()