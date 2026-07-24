"""Quick test"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")

folder = "C:/Users/Guilherme/Documents/GLOSAS/RECEBIMENTO GLOSAS/2026/REF. - 06.2026/87"
f = os.path.join(folder, os.listdir(folder)[0])
print(f"File: {f}")

from services.parser_glosas import parse_planilha_glosas
r = parse_planilha_glosas(f)
print(f"Total registros: {r['total_lidos']}")
print("5 primeiros:")
for x in r["registros"][:5]:
    print(f"  {x['colaborador_nome'][:30]} | {x['data_falta']} | dias:{x['quantidade_dias']} | R${x['valor_total']}")
