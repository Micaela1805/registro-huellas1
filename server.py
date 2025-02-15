from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import json
import time

app = Flask(__name__)

# 🔹 Configuración de Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1Gnh6cUqXK76pQGoq6tS9ZVJXPiN7eYzI8kca_HA")

credenciales_json = os.getenv("GOOGLE_CREDENTIALS")
if not credenciales_json:
    raise ValueError("⚠️ No se encontraron las credenciales en las variables de entorno.")

credentials_info = json.loads(credenciales_json)
credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
service = build("sheets", "v4", credentials=credentials)
sheet = service.spreadsheets()

# 🔹 Obtener huellas registradas en Google Sheets
def obtener_hashes_registrados():
    try:
        result = sheet.values().get(spreadsheetId=SHEET_ID, range="RegistroHuella!A:B").execute()
        valores = result.get("values", [])

        huellas_db = {fila[1]: fila[0] for fila in valores if len(fila) > 1}
        return huellas_db

    except Exception as e:
        print(f"❌ Error al obtener hashes de Google Sheets: {e}")
        return {}

@app.route("/verificar", methods=["POST"])
def verificar_huella():
    data = request.get_json()
    huella_capturada = data.get("huella")

    if not huella_capturada:
        return jsonify({"status": "error", "message": "No se recibió una huella válida"}), 400

    huellas_registradas = obtener_hashes_registrados()

    if huella_capturada in huellas_registradas:
        dni = huellas_registradas[huella_capturada]
        print(f"✅ Huella reconocida. DNI: {dni}")

        row = [[dni, time.strftime("%d/%m/%Y"), time.strftime("%H:%M:%S"), "Almuerzo"]]
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="RegistroHuella!C:F",
            valueInputOption="RAW",
            body={"values": row},
        ).execute()

        return jsonify({"status": "success", "dni": dni, "message": "Huella validada"}), 200
    else:
        print("❌ Huella no reconocida")
        return jsonify({"status": "error", "message": "Huella no encontrada"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000, debug=True)


