import json
import requests

# =====================================================================
# RUTAS DE ENRUTAMIENTO (API GATEWAYS)
# =====================================================================

# ⚠️ URL DE LA TABLA 2 (ODS ALDO - Servidores Públicos - 26 Columnas)
URL_ALDO = "https://script.google.com/macros/s/AKfycbz51-TP1VBzOUIa1P7RlkUF73q5LSfhEvz-ePY1evzH-tudNTYjBf6hLGXn96bslyf_xw/exec"

# ⚠️ URL DE LA TABLA 3 (STAGING AREA GLOBAL - 17 Columnas)
URL_GLOBAL = "https://script.google.com/macros/s/AKfycbzmOjGCQlDdZzuTTjrGJLv_VdjUojFnizDR1sGxPY3onJsuRC-SfPLf4IefPKXU3z3gFQ/exec"


def obtener_calificaciones():
    """Descarga el JSON con las calificaciones del Examen Diagnóstico a través del puente de Aldo."""
    try:
        payload = {"action": "obtener_calificaciones"}
        headers = {'Content-Type': 'text/plain;charset=utf-8'}

        response = requests.post(
            URL_ALDO, data=json.dumps(payload), headers=headers)

        if response.status_code == 200:
            res = response.json()
            if res.get("status") == "success":
                return res.get("data", []), None
            return [], res.get("message")
        return [], f"Error HTTP: {response.status_code}"
    except Exception as e:
        return [], str(e)


def inyectar_datos_limpios(df_buenos, df_anomalias, ruta="aldo"):
    """
    Transmisor Aislado: Envía la data procesada a la ruta especificada.
    El desacoplamiento evita la contaminación cruzada entre bases de datos.
    """
    try:
        registros_buenos = df_buenos.fillna('').astype(str).to_dict(
            orient='records') if not df_buenos.empty else []
        registros_anomalias = df_anomalias.fillna('').astype(str).to_dict(
            orient='records') if not df_anomalias.empty else []

        if ruta == "global":
            action_id = "ingesta_global"
            url_destino = URL_GLOBAL
        else:
            action_id = "ingesta_etl"
            url_destino = URL_ALDO

        payload = {
            "action": action_id,
            "datos_validos": registros_buenos,
            "datos_anomalias": registros_anomalias
        }

        headers = {'Content-Type': 'text/plain;charset=utf-8'}
        response = requests.post(
            url_destino, data=json.dumps(payload), headers=headers)

        if response.status_code == 200:
            res = response.json()
            if res.get("status") == "success":
                # Rescata las 3 métricas que devuelve Apps Script
                return res.get("insertados_maestra", 0), res.get("insertados_anomalias", 0), res.get("duplicados_omitidos", 0), None
            return 0, 0, 0, res.get("message")
        return 0, 0, 0, f"Error HTTP: {response.status_code}"
    except Exception as e:
        return 0, 0, 0, str(e)
