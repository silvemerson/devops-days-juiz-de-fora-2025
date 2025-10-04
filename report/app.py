# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, redirect, url_for, request, send_from_directory
import subprocess
import markdown
import os

app = Flask(__name__)

RELATORIO_DIR = "relatorios"

TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8" />
    <title>Relatório k8sgpt — DevOpsDays Juiz de Fora</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        :root {
            --brand: #0d6efd;      /* azul do botão atual */
            --brand-dark: #0a58ca;
            --accent: #00a0df;     /* tom que conversa com o logo devopsdays */
            --bg: #ffffff;
            --ink: #111111;
            --muted: #6b7280;
            --card: #ffffff;
            --card-border: #e5e7eb;
        }
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
            margin: 0; background: var(--bg); color: var(--ink);
        }
        .wrap {
            max-width: 980px; margin: 32px auto; padding: 0 20px;
        }
        /* Header com logo e título do evento */
        .evt {
            display: grid; grid-template-columns: 96px 1fr; gap: 16px; align-items: center;
            padding: 16px; border: 1px solid var(--card-border); border-radius: 12px;
            background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
        }
        .evt img {
            width: 96px; height: 96px; object-fit: contain; background: #fff; border-radius: 12px; padding: 6px;
            border: 1px solid var(--card-border);
        }
        .evt h1 {
            margin: 0 0 6px 0; font-size: 1.5rem; line-height: 1.2;
        }
        .evt p {
            margin: 0; color: var(--muted);
        }
        /* Barra de ações */
        .actions {
            margin: 18px 0 8px;
            display: flex; gap: 10px; flex-wrap: wrap;
        }
        .btn {
            padding: 10px 16px; background: var(--brand); color: #fff; border: 0;
            border-radius: 8px; cursor: pointer; font-weight: 600;
        }
        .btn:hover { background: var(--brand-dark); }
        .btn-secondary {
            background: #10b981; /* verde download */
        }
        .btn-secondary:hover { background: #059669; }
        /* Conteúdo/relatório */
        .card {
            border: 1px solid var(--card-border); border-radius: 12px; padding: 20px; background: var(--card);
        }
        pre, code {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        }
        pre {
            background-color: #f6f8fa; padding: 12px; border-radius: 8px; overflow:auto;
        }
        table {
            width: 100%; border-collapse: collapse; margin: 12px 0;
        }
        table th, table td {
            border: 1px solid #e5e7eb; padding: 8px; text-align: left;
        }
        hr { border: 0; border-top: 1px solid var(--card-border); margin: 20px 0; }
        .erro-box {
            background: #fef2f2; color: #7f1d1d; padding: 16px; border-radius: 10px; border: 1px solid #fecaca;
            white-space: pre-wrap;
        }
        .muted { color: var(--muted); font-size: .95rem; }
        /* Impressão */
        @media print {
            .actions, .download-link, form { display: none !important; }
            .wrap { margin: 0; }
            body { background: #fff; }
            .evt { border-color: #ddd; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <!-- Cabeçalho do evento -->
        <section class="evt">
            <img src="{{ event_logo_url or 'https://devopsdays.org/events/2025-juiz-de-fora/images/event-logo.png' }}"
                 alt="DevOpsDays Juiz de Fora 2025 - Logo" />
            <div>
                <h1>{{ event_title or "Relatório k8sgpt — DevOpsDays Juiz de Fora 2025" }}</h1>
                {% if generated_at %}
                    <p class="muted">Gerado em {{ generated_at }}</p>
                {% else %}
                    <p class="muted">Relatório técnico para a apresentação / demo</p>
                {% endif %}
            </div>
        </section>

        <!-- Ações -->
        <div class="actions">
            <form method="post" action="{{ url_for('executar_analise') }}">
                <button class="btn">Executar nova análise</button>
            </form>

            {% if relatorio %}
                <a href="{{ url_for('baixar_relatorio', arquivo=relatorio_arquivo) }}"
                   class="btn btn-secondary download-link" download>
                    Baixar relatório (.md)
                </a>
            {% endif %}
        </div>

        <div class="card">
            {% if erro %}
                <div class="erro-box">
                    <h2>Erro ao executar análise</h2>
                    <h3>Saída padrão (stdout):</h3>
                    <pre>{{ erro.stdout }}</pre>
                    <h3>Erro padrão (stderr):</h3>
                    <pre>{{ erro.stderr }}</pre>
                </div>
            {% else %}
                {% if relatorio %}
                    {{ relatorio|safe }}
                {% else %}
                    <p>Nenhum relatório gerado ainda. Clique em <strong>Executar nova análise</strong>.</p>
                {% endif %}
            {% endif %}
        </div>

        {% if relatorio %}
            <p class="muted" style="margin-top:12px;">
                Dica: use <kbd>Ctrl</kbd>+<kbd>P</kbd> para imprimir/gerar PDF sem botões.
            </p>
        {% endif %}
    </div>
</body>
</html>
"""


def obter_relatorio_mais_recente():
    """Retorna o caminho do relatório mais recente (com base no timestamp de modificação)."""
    if not os.path.exists(RELATORIO_DIR):
        return None
    arquivos = [
        os.path.join(RELATORIO_DIR, f)
        for f in os.listdir(RELATORIO_DIR)
        if f.startswith("relatorio_k8sgpt") and f.endswith(".md")
    ]
    if not arquivos:
        return None
    return max(arquivos, key=os.path.getmtime)

@app.route("/")
def index():
    show = request.args.get("show") == "1"
    relatorio_html = None
    relatorio_arquivo = None

    if show:
        caminho_relatorio = obter_relatorio_mais_recente()
        if caminho_relatorio and os.path.exists(caminho_relatorio):
            with open(caminho_relatorio, "r", encoding="utf-8") as f:
                md_content = f.read().strip()
                if md_content:
                    relatorio_html = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
                    relatorio_arquivo = os.path.basename(caminho_relatorio)

    return render_template_string(TEMPLATE_HTML, relatorio=relatorio_html, relatorio_arquivo=relatorio_arquivo, erro=None)

@app.route("/executar", methods=["POST"])
def executar_analise():
    try:
        # 1. gera relatório
        subprocess.run(["python3", "coleta_relatorio.py"],
                       capture_output=True, text=True, check=True)

        # 2. identifica o arquivo mais recente
        md_path = obter_relatorio_mais_recente()
        # if md_path:
        #     # 3. envia para o GitLab
        #     subprocess.run(["python3", "git_sync.py", md_path],
        #                    capture_output=True, text=True, check=True)

        return redirect(url_for("index", show=1))

    except subprocess.CalledProcessError as e:
        erro = {"stdout": e.stdout, "stderr": e.stderr}
        return render_template_string(TEMPLATE_HTML,
                                      relatorio=None,
                                      relatorio_arquivo=None,
                                      erro=erro)

@app.route("/baixar_relatorio/<arquivo>")
def baixar_relatorio(arquivo):
    diretorio = os.path.abspath(RELATORIO_DIR)
    try:
        return send_from_directory(diretorio, arquivo, as_attachment=True)
    except FileNotFoundError:
        return "<h2>Arquivo não encontrado.</h2>", 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)
