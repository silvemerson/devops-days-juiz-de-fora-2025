# -*- coding: utf-8 -*-
import json
import subprocess
from datetime import datetime
import os
import requests

os.makedirs("relatorios", exist_ok=True)
os.makedirs("logs", exist_ok=True)

def nome_arquivo_com_timestamp(prefixo, ext="md"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"relatorios/{prefixo}_{ts}.{ext}"

def nome_log_com_timestamp():
    ts = datetime.now().strftime("%Y%m%d")
    return f"logs/k8sgpt-summary_{ts}.log"


OUTPUT_JSON = "k8sgpt_output.json"
RELATORIO_MD = nome_arquivo_com_timestamp("relatorio_k8sgpt")
RELATORIO_MELHORADO = nome_arquivo_com_timestamp("relatorio_k8sgpt_melhorado")
LOG_RESUMO = nome_log_com_timestamp()

print("Executando k8sgpt analyze...")
with open(OUTPUT_JSON, "w") as f:
    cmd = [
        "k8sgpt","analyze",
        "--explain",
        "--language=portuguese",
        "--output=json"
    ]
    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)

if result.returncode != 0:
    print("Erro ao executar k8sgpt:")
    print(result.stderr.decode())
    exit(1)

try:
    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
except json.JSONDecodeError:
    print("Erro ao decodificar JSON gerado pelo k8sgpt.")
    exit(1)

if not data.get("results") or not isinstance(data["results"], list):
    print("Nenhum problema detectado.")
    exit(0)

markdown = "## Relatório de Problemas Detectados pelo K8sGPT\n\n"
log_lines = []

for prob in data["results"]:
    kind = prob.get("kind", "N/A")
    name = prob.get("name", "N/A")
    try:
        ns, obj_name = name.split("/")
    except ValueError:
        ns = "default"
        obj_name = name

    error = prob.get("error", [{}])[0].get("Text", "Sem descrição de erro")
    detalhes = prob.get("details", "").strip()

    markdown += f"""
### Análise realizada:
- **Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Namespace**: `{ns}`
- **Tipo de Recurso**: `{kind}`
- **Nome**: `{obj_name}`

---

### Erro Detectado:
{error}

---

### Explicação:
{detalhes}

---
"""

    log_lines.append(f"[{datetime.now().isoformat()}] {ns}/{obj_name}: {error}")

markdown += "\n_Gerado automaticamente a partir do k8sgpt_output.json_\n"

with open(RELATORIO_MD, "w", encoding="utf-8") as f:
    f.write(markdown)

with open(LOG_RESUMO, "a", encoding="utf-8") as f:
    for line in log_lines:
        f.write(line + "\n")

print(f"Relatório gerado: {RELATORIO_MD}")
print(f"Log resumido salvo: {LOG_RESUMO}")

def melhorar_relatorio(texto_markdown):
    prompt = f"""
Reescreva esse relatório do k8sgpt de forma mais clara, como se fosse um DevOps Engineer ou SRE, inclua bastante detalhes baseado nas boas práticas do Kubernetes. Use linguagem técnica acessível, como se fosse apresentar para um cliente leigo, destaque as ações sugeridas e gere um resumo executivo no final:

{texto_markdown}
    """
    try:
        resposta = requests.post("http://127.0.0.1:11434/api/generate", json={
            "model": "llama3.1:latest",
            "prompt": prompt,
            "stream": False
        })
        resposta_json = resposta.json()

        print("DEBUG: Resposta da API Ollama:", resposta_json)

        if "response" in resposta_json:
            return resposta_json["response"]
        else:
            print("Chave 'response' não encontrada na resposta da API.")
            return None
    except Exception as e:
        print("Não foi possível melhorar o relatório com o Ollama:", str(e))
        return None

melhorado = melhorar_relatorio(markdown)
if melhorado:
    with open(RELATORIO_MELHORADO, "w", encoding="utf-8") as f:
        f.write(melhorado)
    print(f"Relatório melhorado salvo em: {RELATORIO_MELHORADO}")
else:
    print("Não foi possível gerar o relatório melhorado.")
