from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
from datetime import datetime
import os
import pickle
import base64
import re
import uuid

app = Flask(__name__)
app.secret_key = "chave_super_secreta"

# Filename is managed per user session.
@app.context_processor
def inject_now():
    return {
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "filename": session.get("filename")
    }

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files["file"]
        if file and file.filename.endswith(".csv"):
            try:
                df = pd.read_csv(file, dtype={"cpf": str})
                expected_cols = ["cpf", "nome", "plano", "setor_checkin", "data_checkin", "checkin_status", "data_update"]
                # Normalize column names: strip whitespace and lowercase
                df.columns = [col.strip().lower() for col in df.columns]
                if set(df.columns) != set(expected_cols):
                    flash("Erro: Estrutura do CSV inválida!", "danger")
                else:
                    # Padroniza CPF como string (mantém zeros à esquerda)
                    df["cpf"] = df["cpf"].astype(str)
                    df.set_index("cpf", inplace=True)
                    # Salva o DataFrame em arquivo
                    upload_path = os.path.join("uploads", "data.pkl")
                    df.to_pickle(upload_path)
                    session['filename'] = file.filename
                    # Gera um identificador único para a sessão
                    if 'session_id' not in session:
                        session['session_id'] = str(uuid.uuid4())
                    # Salva o caminho do arquivo da base na sessão
                    user_db_path = os.path.join("uploads", f"data_{session['session_id']}.pkl")
                    df.to_pickle(user_db_path)
                    session['database_path'] = user_db_path
                    return redirect(url_for("consulta"))
            except Exception as e:
                flash(f"Erro ao ler o arquivo: {e}", "danger")
        else:
            flash("Envie um arquivo CSV válido!", "danger")
    return render_template("upload.html")

@app.route("/consulta", methods=["GET", "POST"])
def consulta():
    resultado = None
    registros_list = []
    # Carrega o DataFrame do arquivo
    database = None
    user_db_path = session.get('database_path')
    # Se não houver arquivo carregado na sessão, redireciona para a tela inicial
    if not session.get('filename') or not user_db_path or not os.path.exists(user_db_path):
        flash("Faça o upload do arquivo antes de consultar.", "danger")
        return redirect(url_for("upload"))
    try:
        database = pd.read_pickle(user_db_path)
    except Exception:
        database = None
    if request.method == "POST":
        cpf = request.form.get("cpf")
        if cpf is not None:
            cpf = re.sub(r'[^0-9]', '', cpf.strip())
        row = None
        if database is not None:
            try:
                # Busca sempre por string
                row = database.loc[str(cpf)]
            except KeyError:
                row = None

        if row is None or (isinstance(row, pd.Series) and row.empty):
            flash(f"CPF {cpf} não encontrado na base.", "danger")
            resultado = None
        else:
            # Sempre itera sobre todos os registros encontrados
            if isinstance(row, pd.DataFrame):
                for _, row_data in row.iterrows():
                    status = row_data["checkin_status"]
                    status_class = (
                        "status-ok" if status == "Realizado" else
                        "status-cancelado" if status == "Cancelado" else
                        "status-pendente"
                    )
                    registros_list.append({
                        "nome": row_data.get("nome", ""),
                        "cpf": cpf,
                        "plano": row_data.get("plano", ""),
                        "status": status,
                        "status_class": status_class,
                        "setor_checkin": row_data.get("setor_checkin", ""),
                        "data_checkin": row_data.get("data_checkin", ""),
                        "data_update": row_data.get("data_update", "")
                    })
            else:
                # Apenas um registro
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
    return render_template("consulta.html", registros=registros_list, resultado=resultado)
# For development only: do not use this in production
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    app.run(host="0.0.0.0", port=port)
