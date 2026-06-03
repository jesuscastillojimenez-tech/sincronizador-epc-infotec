# ============================================================================
# ARCHIVO: google_sync.py
# ============================================================================
import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import uuid  # <-- Importante: Librería nativa para generar folios únicos


def conectar_sheets():
    """Autenticación cifrada usando los secretos locales de Streamlit (Secrets)."""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive'
    ]
    try:
        cred_dict = dict(st.secrets["gcloud_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            cred_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"[-] Error de seguridad en conexión de API: {e}")
        return None


def sincronizar_datos_seguro(cliente, id_documento, nombre_hoja, df_nuevo):
    """Inyección Inteligente: Rellena perfiles y manda anomalías a la bitácora estructurada."""
    try:
        hoja_maestra = cliente.open_by_key(id_documento).worksheet(nombre_hoja)

        # Validar que exista la hoja de anomalías
        try:
            hoja_anomalias = cliente.open_by_key(
                id_documento).worksheet("Casos_Extraordinarios_Curp")
        except Exception:
            st.error(
                "No se encontró la hoja 'Casos_Extraordinarios_Curp' en el documento.")
            return 0, 0

        todos_los_datos = hoja_maestra.get_all_values()
        encabezados_oficiales = todos_los_datos[0] if todos_los_datos else []

        if not encabezados_oficiales:
            st.error("La hoja de destino está vacía o no tiene encabezados.")
            return 0, 0

        # 1. Crear mapa de CURPs existentes en la Maestra
        curps_existentes = {}
        for i, fila in enumerate(todos_los_datos):
            if i == 0:
                continue
            if len(fila) > 1:
                curp = str(fila[1]).strip().upper()
                nombre_existente = str(
                    fila[2]).strip() if len(fila) > 2 else ""
                correo_examen = str(fila[6]).strip() if len(fila) > 6 else ""

                curps_existentes[curp] = {
                    "fila_real": i + 1,
                    "falta_datos_forminator": (nombre_existente == ""),
                    "correo_examen": correo_examen
                }

        df_procesado = df_nuevo.fillna('').astype(str)
        df_alineado = df_procesado[encabezados_oficiales]

        anomalias_registros = []
        actualizaciones_batch = []

        # 2. Clasificación de Tráfico
        for index, row in df_alineado.iterrows():
            curp_alumno = str(row['CURP']).strip().upper()
            if not curp_alumno:
                continue

            if curp_alumno in curps_existentes:
                datos_existentes = curps_existentes[curp_alumno]

                # ACTUALIZAMOS si el esqueleto del examen está vacío
                if datos_existentes["falta_datos_forminator"]:
                    fila_actualizar = datos_existentes["fila_real"]
                    datos_a_inyectar = row.values.tolist()[:12]

                    # No sobreescribir el correo validado del examen
                    if datos_existentes["correo_examen"]:
                        datos_a_inyectar[6] = datos_existentes["correo_examen"]

                    actualizaciones_batch.append({
                        'range': f'A{fila_actualizar}:L{fila_actualizar}',
                        'values': [datos_a_inyectar]
                    })
            else:
                # ESTRUCTURA DE BITÁCORA DE ANOMALÍAS (Solo 6 columnas)
                id_unico = f"INC-{str(uuid.uuid4())[:6].upper()}"
                nombre_forminator = str(row.get('Nombre Completo', ''))

                fila_anomalia = [
                    id_unico,                                       # 1. ID_Incidente
                    curp_alumno,                                    # 2. CURP_Conflicto
                    # 3. Tipo_Anomalía
                    "Falta Examen (Sin registro en BD Maestra)",
                    nombre_forminator,                              # 4. Nombre_Solicitante_A
                    "",                                             # 5. Nombre_Solicitante_B
                    "Pendiente"                                     # 6. Estatus_Resolución
                ]
                anomalias_registros.append(fila_anomalia)

        # 3. Inyección de Anomalías (Excepciones)
        insertados_anomalias = len(anomalias_registros)
        if insertados_anomalias > 0:
            hoja_anomalias.append_rows(
                anomalias_registros, value_input_option='USER_ENTERED')

        # 4. Inyección de Actualizaciones en Maestra
        actualizados_maestra = len(actualizaciones_batch)
        if actualizados_maestra > 0:
            hoja_maestra.batch_update(
                actualizaciones_batch, value_input_option='USER_ENTERED')

        return actualizados_maestra, insertados_anomalias

    except Exception as e:
        st.error(f"Error crítico en Sincronización: {e}")
        return 0, 0
