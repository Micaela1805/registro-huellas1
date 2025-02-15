from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from google.oauth2 import service_account
import usb.core
import usb.util
import os
import json
import time

app = Flask(__name__)

# 🔹 Configuración de Google Sheets desde variables de entorno
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1Gnh6cUqXK76pQGoq6tS9ZVJXPiN7eYzI8kca_HA")  # Reemplázalo si es necesario

credenciales_json = os.getenv("GOOGLE_CREDENTIALS")
if not credenciales_json:
    raise ValueError("⚠️ No se encontraron las credenciales en las variables de entorno.")

credentials_info = json.loads(credenciales_json)
credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
service = build("sheets", "v4", credentials=credentials)
sheet = service.spreadsheets()

# 🔹 Configuración del lector de huellas ZKTeco Live20R
VENDOR_ID = 0x1b55
PRODUCT_ID = 0x0120

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if dev is None:
    raise ValueError("⚠️ Lector de huellas ZKTeco Live20R no encontrado.")

try:
    dev.set_configuration()
    print("✅ Lector de huellas conectado correctamente.")
except usb.core.USBError as e:
    print(f"❌ Error al configurar el lector: {e}")

# 🔹 Función para capturar huella
def capturar_huella():
    print("🔹 Esperando huella...")

    try:
        data = dev.read(0x82, 512, timeout=5000)  # Ajusta el tamaño si es necesario
        huella_hash = "".join(format(x, "02x") for x in data[:16])  # Tomamos solo los primeros 16 bytes

        print(f"✅ Huella capturada: {huella_hash}")
        return huella_hash

    except usb.core.USBError as e:
        print(f"❌ Error al leer la huella: {e}")
        return None

# 🔹 Función para obtener los hashes registrados en Google Sheets
def obtener_hashes_registrados():
    try:
        result = sheet.values().get(spreadsheetId=SHEET_ID, range="RegistroHuella!A:B").execute()
        valores = result.get("values", [])

        # Convertir la hoja a un diccionario {hash: DNI}
        huellas_db = {fila[1]: fila[0] for fila in valores if len(fila) > 1}
        return huellas_db

    except Exception as e:
        print(f"❌ Error al obtener hashes de Google Sheets: {e}")
        return {}

@app.route("/verificar", methods=["GET"])
def verificar_huella():
    huella_capturada = capturar_huella()
    if not huella_capturada:
        return jsonify({"status": "error", "message": "No se pudo capturar la huella"}), 400

    # 🔹 Obtener huellas registradas
    huellas_registradas = obtener_hashes_registrados()

    # 🔹 Verificar si la huella capturada existe en Google Sheets
    if huella_capturada in huellas_registradas:
        dni = huellas_registradas[huella_capturada]
        print(f"✅ Huella reconocida. DNI: {dni}")

        # 🔹 Registrar la asistencia en Google Sheets
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

# 🔹 Nuevo endpoint para probar googleapiclient
@app.route("/test-googleapi")
def test_google_api():
    try:
        from googleapiclient.discovery import build
        return jsonify({"status": "success", "message": "Google API client importado correctamente"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000, debug=True)



