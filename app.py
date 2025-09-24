from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "chave_super_secreta"

# Senha fixa
PASSWORD = "1234"

# Variáveis globais
database = None
filename = None

@app.context_processor
def inject_now():
    return {"date": datetime.now().strftime("%d/%m/%Y %H:%M"), "filename": filename}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha == PASSWORD:
            return redirect(url_for("upload"))
        else:
            flash("Senha incorreta!", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    # Aqui você pode limpar a sessão ou apenas redirecionar para a página inicial
    session.clear()  # só se estiver usando sessões
    return redirect(url_for("/"))

@app.route("/upload", methods=["GET", "POST"])
def upload():
    global database, filename
    if request.method == "POST":
        file = request.files["file"]
        if file and file.filename.endswith(".csv"):
            try:
                df = pd.read_csv(file, dtype=str)

                expected_cols = ["cpf","nome","plano","setor_checkin","data_checkin","checkin_status","data_update"]
                if list(df.columns) != expected_cols:
                    flash("Erro: Estrutura do CSV inválida!", "danger")
                else:
                    df.set_index("cpf", inplace=True)
                    database = df
                    filename = file.filename
                    return redirect(url_for("consulta"))
            except Exception as e:
                flash(f"Erro ao ler o arquivo: {e}", "danger")
        else:
            flash("Envie um arquivo CSV válido!", "danger")
    return render_template("upload.html")

@app.route("/consulta", methods=["GET", "POST"])
def consulta():
    global database
    resultado = None
    registros_list = []
    if request.method == "POST":
        cpf = request.form.get("cpf")
        if database is not None:
            try:
                registros = database.loc[[cpf]]
            except KeyError:
                registros = pd.DataFrame()

            if registros.empty:
                resultado = f"<p class='error'>CPF {cpf} não encontrado na base.</p>"
            else:
                for _, row in registros.iterrows():
                    status = row["checkin_status"]
                    status_class = (
                        "status-ok" if status == "Realizado" else
                        "status-cancelado" if status == "Cancelado" else
                        "status-pendente"
                    )
                    registros_list.append({
                        "nome": row.get("nome", ""),
                        "cpf": cpf,
                        "plano": row.get("plano", ""),
                        "status": status,
                        "status_class": status_class,
                        "setor_checkin": row.get("setor_checkin", ""),
                        "data_checkin": row.get("data_checkin", ""),
                        "data_update": row.get("data_update", "")
                    })
    return render_template("consulta.html", registros=registros_list, resultado=resultado)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
