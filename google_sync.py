# ============================================================================
# ARCHIVO: google_sync.py
# ============================================================================
import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials


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
    """Inyección Inteligente: Agrega nuevos y rellena a los que hicieron el examen primero."""
    try:
        hoja = cliente.open_by_key(id_documento).worksheet(nombre_hoja)
        todos_los_datos = hoja.get_all_values()
        encabezados_oficiales = todos_los_datos[0] if todos_los_datos else []

        if not encabezados_oficiales:
            st.error("La hoja de destino está vacía o no tiene encabezados.")
            return 0, 0

        # 1. Crear mapa de CURPs existentes y detectar si les falta el nombre (Fila de Examen)
        curps_existentes = {}
        for i, fila in enumerate(todos_los_datos):
            if i == 0:
                continue  # Saltar encabezados
            if len(fila) > 1:
                curp = str(fila[1]).strip().upper()
                nombre_existente = str(
                    fila[2]).strip() if len(fila) > 2 else ""

                # Registramos su fila real en Google Sheets (i + 1)
                curps_existentes[curp] = {
                    "fila_real": i + 1,
                    # True si hizo el examen antes del forminator
                    "falta_datos_forminator": (nombre_existente == "")
                }

        df_procesado = df_nuevo.fillna('').astype(str)
        df_alineado = df_procesado[encabezados_oficiales]

        nuevos_registros = []
        actualizaciones_batch = []

        # 2. Clasificación de Tráfico
        for index, row in df_alineado.iterrows():
            curp_alumno = str(row['CURP']).strip().upper()
            if not curp_alumno:
                continue

            if curp_alumno in curps_existentes:
                datos_existentes = curps_existentes[curp_alumno]
                # Si el usuario ya está pero su campo nombre está vacío, lo ACTUALIZAMOS
                if datos_existentes["falta_datos_forminator"]:
                    fila_actualizar = datos_existentes["fila_real"]
                    # Solo tomamos de la columna A a la L (los 12 primeros datos de Forminator)
                    # para NO borrar los resultados del examen que están de la M a la Z
                    datos_a_inyectar = row.values.tolist()[:12]

                    actualizaciones_batch.append({
                        'range': f'A{fila_actualizar}:L{fila_actualizar}',
                        'values': [datos_a_inyectar]
                    })
            else:
                # Si no está en la base, es una inserción nueva completa
                nuevos_registros.append(row.values.tolist())

        # 3. Inyección masiva (Append)
        insertados = len(nuevos_registros)
        if insertados > 0:
            ultima_fila_real = len(todos_los_datos)
            siguiente_fila = ultima_fila_real + 1
            letra_fin = gspread.utils.rowcol_to_a1(
                1, len(encabezados_oficiales)).replace('1', '')
            rango_destino = f"A{siguiente_fila}:{letra_fin}{siguiente_fila + insertados - 1}"

            hoja.update(
                range_name=rango_destino,
                values=nuevos_registros,
                value_input_option='USER_ENTERED'
            )

        # 4. Inyección de Actualizaciones (Update Batch)
        actualizados = len(actualizaciones_batch)
        if actualizados > 0:
            hoja.batch_update(actualizaciones_batch,
                              value_input_option='USER_ENTERED')

        return insertados, actualizados

    except Exception as e:
        st.error(f"Error crítico en Sincronización: {e}")
        return 0, 0
