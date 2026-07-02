from import_col.cols import cols
from sqlalchemy import create_engine, text
from os import getenv
from dotenv import load_dotenv
from datetime import datetime as dt
from tqdm import tqdm
from re import sub

load_dotenv()

total = len(cols["empregados"])

def create_cost_centers():
    cont = 0
    up = 0
    with tqdm(total=total, desc="Cadastrando centros de custo") as pbar:
        centros_de_custos = []
        for item in cols["empregados"]:
            centros_de_custos.append({
                "id": item["centro_custo_num"],
                "local": item["centro_custo"],
                "dpto": item["departamento_codigo"],
                "cidade_id": item["cidade_id"],
        })
            
        # -------------------------------------------------------------- #
        
        for item in list({d["id"]: d for d in centros_de_custos}.values()):
            id = item.get("id")
            local = item.get("local")
            dpto = item.get("dpto")
            dpto = dpto if dpto else 0
            cidade_id = item.get("cidade_id", 0)

            exists = conn.execute(text(f"SELECT id FROM centro_de_custo where id = {id}")).first()
            exists = exists[0] if exists else False
            if exists:
                conn.execute(text(f"UPDATE centro_de_custo SET local = '{local}', departamento = {dpto}, cidade_id = {cidade_id} WHERE id = {id}"))
                up += 1
            else:
                conn.execute(text(f"INSERT INTO centro_de_custo(id, local, departamento, cidade_id) VALUES({id}, '{local}', {dpto}, {cidade_id})"))
                cont += 1            
            pbar.update(1)
    conn.commit()
    return cont, up


def create_cobs():
    cont = 0
    up = 0
    with tqdm(total=total, desc="Sincronizando os Colaboradores") as pbar:
        for item in cols["empregados"]:
            mat = item.get("codigo")
            nome = item.get("nome")
            center_id = item.get("centro_custo_num")
            dt_admissao = item.get("data_admissao")
            cargo = item.get("cargo")
            situacao = item.get("situacao_codigo")

            admissao = dt.now().strptime(dt_admissao, "%d/%m/%Y")
            nome = sub(r"[\d'\".,]", "", nome)

            exists = conn.execute(text(f"""SELECT ID FROM COLABORADORES WHERE MATRICULA = '{mat}' """)).first()
            exists = exists[0] if exists else False
            cargo_id = conn.execute(text(f"""SELECT ID FROM CARGOS WHERE NOME = '{cargo}' """)).first()
            cargo_id = cargo_id[0] if cargo_id else 0

            if exists:
                conn.execute(text(f"""UPDATE COLABORADORES SET NOME = '{nome}', CENTRO_ID = {center_id}, data_admissao = '{admissao}', cargo = {cargo_id}, situacao = {situacao} WHERE MATRICULA = '{mat}' """))
                up += 1
            else:
                conn.execute(text(f"""INSERT INTO COLABORADORES(MATRICULA, NOME, CENTRO_ID, DATA_ADMISSAO, CARGO, SITUACAO) VALUES('{mat}', '{nome}', {center_id}, '{admissao}', {situacao}, {cargo_id})"""))
                cont += 1
            pbar.update(1)
    conn.commit()
    return cont, up

with create_engine(getenv("DB_URI")).connect() as conn: 
    cont, up = create_cobs()

    print("="*50)
    print("Status da Sincronização de Colaborades:")
    print("="*50)
    print("Criados: ", cont)
    print("="*50)
    print("Updates: ", up)
    print("="*50)