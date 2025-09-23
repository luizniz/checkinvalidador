import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd

app = Flask(__name__)
app.secret_key = "troque_essa_chave_por_uma_segura"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Senha fixa
PASSWORD = "1234"

# Estrutura esperada (exatamente nessa primeira linha, nomes em lowercase)
EXPECTED_COLUMNS = [
    "cpf",
    "nome",
    "plano",
    "setor_checkin",
    "data_checkin",
    "checkin_status",
    "data_update",
]


def normalize_col_name(col):
    """Remove espaços e BOM da coluna"""
    return str(col).strip().lstrip("\ufeff")


def digits_only(s):
    return re.sub(r"\D", "", str(s))


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        senha = request.form.get("senha", "")
        if senha == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("upload"))
        else:
            flash("Senha incorreta!", "danger")
    return render_template("login.html", date=datetime.now().strftime("%d/%m/%Y %H:%M"), filename=session.get("csv_name"))


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo enviado.", "danger")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado.", "danger")
            return redirect(request.url)

        if not file.filename.lower().endswith(".csv"):
            flash("Envie um arquivo .csv", "danger")
            return redirect(request.url)

        try:
            # Lê o CSV como strings (preserva zeros à esquerda)
            df = pd.read_csv(file, dtype=str)
        except Exception as e:
            flash(f"Erro ao ler CSV: {e}", "danger")
            return redirect(request.url)

        # Normaliza nomes de coluna (remove BOM/espacos)
        normalized = [normalize_col_name(c) for c in df.columns]
        df.columns = normalized

        # Verifica estrutura (ordem e nomes devem bater exatamente com EXPECTED_COLUMNS)
        if df.columns.tolist() != EXPECTED_COLUMNS:
            expected_display = '","'.join(EXPECTED_COLUMNS)
            found_display = '","'.join(df.columns.tolist())
            flash(
                ("Estrutura inválida. Primeira linha deve ser exatamente:\n"
                 f"\"{expected_display}\".\nColunas encontradas:\n\"{found_display}\""),
                "danger"
            )
            return redirect(request.url)

        # Garante as colunas no mesmo formato e cria cpf_digits para busca
        df = df.copy()
        df["cpf"] = df["cpf"].astype(str)
        df["cpf_digits"] = df["cpf"].apply(lambda x: digits_only(x).zfill(11))

        # Salva DataFrame processado em arquivo para não depender apenas de variável global
        data_path = os.path.join(UPLOAD_FOLDER, "data.pkl")
        df.to_pickle(data_path)

        # Guarda nome do arquivo na sessão para aparecer no rodapé
        session["csv_name"] = file.filename

        flash("Base carregada com sucesso!", "success")
        return redirect(url_for("consulta"))

    return render_template("upload.html", date=datetime.now().strftime("%d/%m/%Y %H:%M"), filename=session.get("csv_name"))


@app.route("/consulta", methods=["GET", "POST"])
def consulta():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    data_path = os.path.join(UPLOAD_FOLDER, "data.pkl")
    df = None
    if os.path.exists(data_path):
        try:
            df = pd.read_pickle(data_path)
        except Exception:
            flash("Erro ao carregar a base processada. Refaça o upload.", "danger")
            return redirect(url_for("upload"))
    else:
        flash("Nenhuma base carregada. Faça o upload do CSV.", "warning")
        return redirect(url_for("upload"))

    registros = []
    if request.method == "POST":
        cpf_raw = request.form.get("cpf", "").strip()
        if not cpf_raw:
            flash("Digite um CPF.", "warning")
            return redirect(request.url)

        cpf_digits = digits_only(cpf_raw).zfill(11)
        matches = df[df["cpf_digits"] == cpf_digits]

        if matches.empty:
            flash(f"CPF {cpf_raw} não encontrado na base.", "warning")
        else:
            # Prepara lista de registros para template (mantém ordem original do arquivo)
            for _, row in matches.iterrows():
                status = str(row.get("checkin_status", "")).strip()
                status_norm = status.lower()
                status_class = "success" if status_norm == "realizado" else "error"
                registros.append({
                    "nome": row.get("nome", ""),
                    "plano": row.get("plano", ""),
                    "setor": row.get("setor_checkin", ""),
                    "status": status,
                    "status_class": status_class,
                    "data_checkin": row.get("data_checkin", ""),
                    "data_update": row.get("data_update", ""),
                })

    return render_template(
        "consulta.html",
        date=datetime.now().strftime("%d/%m/%Y %H:%M"),
        filename=session.get("csv_name"),
        registros=registros
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Desconectado.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
