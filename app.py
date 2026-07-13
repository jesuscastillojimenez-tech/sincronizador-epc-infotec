import streamlit as st
import pandas as pd
import io
from difflib import get_close_matches
from core_processing import procesar_cruce_etl_sp, procesar_ingesta_global, CAMPOS_OFICIALES
from google_sync import obtener_calificaciones, inyectar_datos_limpios

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y DISEÑO UX/UI (PALETA INFOTEC)
# ==========================================
st.set_page_config(page_title="Centro de Datos INFOTEC",
                   layout="wide", initial_sidebar_state="expanded")

# Paleta Oficial INFOTEC
C_FONDO = "#002f2a"       # Pantone 627 C (Fondo general)
C_SIDEBAR = "#161a1d"     # Neutral Black C (Fondo de paneles y menú)
C_DORADO = "#ebcf93"      # Pantone 1255 C (Acentos y BD Global)
C_GUINDA = "#612134"      # Pantone 7420 C (Acción Crítica / SP)
C_VERDE = "#1e5b4f"       # Pantone 626 C (Seguridad / Limpiador)

estilo_institucional = f"""
<style>
[data-testid="stAppViewContainer"] {{ background-color: {C_FONDO} !important; }}
[data-testid="stSidebar"] {{ background-color: {C_SIDEBAR} !important; border-right: 3px solid {C_DORADO} !important; }}
h1, h2, h3, h4 {{ color: {C_DORADO} !important; font-weight: 800 !important; font-family: 'Segoe UI', sans-serif; }}
p, label, span, li {{ color: #ffffff !important; font-family: 'Segoe UI', sans-serif; }}

/* Diseño de Botones Amigables */
div[data-testid="stButton"] > button {{
    background-color: {C_SIDEBAR} !important; color: {C_DORADO} !important; 
    border: 2px solid {C_DORADO} !important; border-radius: 8px !important;
    font-weight: 800 !important; transition: all 0.3s ease !important; width: 100% !important;
}}
div[data-testid="stButton"] > button:hover {{ background-color: {C_DORADO} !important; color: {C_SIDEBAR} !important; transform: translateY(-2px); }}

/* Cajas de selección y texto */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{ 
    background-color: {C_SIDEBAR} !important; border: 1px solid {C_DORADO} !important; border-radius: 6px !important;
}}
div[data-baseweb="select"] *, div[data-baseweb="input"] input {{ color: white !important; background-color: transparent !important; }}
div[data-baseweb="select"] svg {{ fill: {C_DORADO} !important; }}

/* Zona de subida de archivos (File Uploader) */
[data-testid="stFileUploadDropzone"] {{ background-color: {C_SIDEBAR} !important; border: 2px dashed {C_DORADO} !important; border-radius: 12px !important; padding: 2rem !important; }}
[data-testid="stFileUploader"] button {{ background-color: {C_DORADO} !important; color: {C_SIDEBAR} !important; border: none !important; font-weight: 800 !important; }}

/* Paneles de estado visuales (Tarjetas de Alerta separadas del color) */
.panel-alerta {{ background-color: {C_SIDEBAR}; padding: 18px 25px; border-radius: 10px; margin-bottom: 25px; box-shadow: 0px 4px 10px rgba(0,0,0,0.4); border-left: 12px solid; }}
.alerta-sp {{ border-color: {C_GUINDA}; }}
.alerta-global {{ border-color: {C_DORADO}; }}
.alerta-limpiador {{ border-color: {C_VERDE}; }}
.alerta-texto {{ color: #ffffff !important; font-size: 1.3rem; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px; }}
.panel-descarga {{ background-color: {C_SIDEBAR}; padding: 20px; border-radius: 12px; border: 2px solid {C_DORADO}; margin-top: 20px; }}
</style>
"""
st.markdown(estilo_institucional, unsafe_allow_html=True)

# ==========================================
# UTILIDADES Y HERRAMIENTAS AMIGABLES
# ==========================================


def sugerir_mapeo(campo_oficial, opciones_excel):
    campo_limpio = campo_oficial.lower().replace("_", " ")
    opciones_limpias = [op.lower() for op in opciones_excel]

    if "correo" in campo_limpio:
        for i, op in enumerate(opciones_limpias):
            if "correo" in op or "e-mail" in op or "email" in op:
                return opciones_excel[i]

    coincidencias = get_close_matches(
        campo_limpio, opciones_limpias, n=1, cutoff=0.6)
    if coincidencias:
        return opciones_excel[opciones_limpias.index(coincidencias[0])]
    return "[Omitir]"


def df_a_excel_multipestana(df_validos, df_errores):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not df_validos.empty:
            df_validos.to_excel(writer, index=False,
                                sheet_name='Datos_Limpios')
        if not df_errores.empty:
            df_errores.to_excel(writer, index=False,
                                sheet_name='Reporte_Errores')
    return output.getvalue()


# ==========================================
# CONTROL DE ACCESO
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "fase" not in st.session_state:
    st.session_state["fase"] = 1


def check_password():
    if st.session_state["autenticado"]:
        return True
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(f"<br><br><div style='text-align: center;'><h1 style='font-size: 3rem;'>INFOTEC</h1><p style='font-size: 1.2rem; color: #ffffff;'>Portal de Gestión y Calidad de Datos</p></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            password = st.text_input("Clave de Acceso", type="password")
            if st.form_submit_button("Ingresar al Portal"):
                if password.strip() == st.secrets.get("access_control", {}).get("admin_password", "EPC2026"):
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas.")
    return False


# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
if check_password():
    st.sidebar.markdown(
        f"<h3 style='color: {C_DORADO}; text-align: center;'>Área de Trabajo</h3>", unsafe_allow_html=True)

    modulo_activo = st.sidebar.radio("Selecciona tu objetivo hoy:", [
        "🏢 Diagnostico/Forminator SP",
        "🌐 BASE DE DATOS GLOBAL STAGING AREA",
        "🧹 Limpiador de Exceles (Uso Local)"
    ])

    if st.sidebar.button("🔄 Empezar de nuevo"):
        st.session_state.clear()
        st.rerun()

    # PSICOLOGÍA DE COLOR: TARJETAS DE ALERTA (Alta Legibilidad)
    if "Diagnostico" in modulo_activo:
        st.markdown(f"<div class='panel-alerta alerta-sp'><p class='alerta-texto'>🏢 Servidores Públicos Forminator/Diagnostico SP</p></div>", unsafe_allow_html=True)
    elif "GLOBAL" in modulo_activo:
        st.markdown(f"<div class='panel-alerta alerta-global'><p class='alerta-texto'>🌐 Ingesta a BD Global (6 Vertientes)</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='panel-alerta alerta-limpiador'><p class='alerta-texto'>🧹 MODO SEGURO: DESCONECTADO DE LA NUBE (Solo Limpiar)</p></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # PASO 1: SELECCIÓN PREVIA, CARGA Y MAPEO
    # ---------------------------------------------------------
    if st.session_state.get("fase", 1) == 1:

        st.markdown("### Define la Vertiente")
        # El índice 0 es "Servidores Publicos". Se auto-selecciona si están en ese módulo.
        default_index = 0 if "Diagnostico" in modulo_activo else 1
        vertiente_global = st.selectbox("¿A qué vertiente pertenecen estos alumnos?",
                                        ["Servidores Publicos", "Poblacion Abierta", "Estancias Profesionales", "Ciberseguridad", "Certificaciones", "Jovenes Tecnologos"], index=default_index)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("### 📁 Sube tu archivo de trabajo")
        archivo_local = st.file_uploader(
            "Arrastra aquí tu Excel o CSV", type=['xlsx', 'csv'])

        if archivo_local:
            if archivo_local.name.endswith('.xlsx'):
                xls = pd.ExcelFile(archivo_local)
                if len(xls.sheet_names) > 1:
                    hoja_seleccionada = st.selectbox(
                        "📑 Tu Excel tiene varias pestañas. ¿Cuál revisamos?", xls.sheet_names)
                    df_crudo = pd.read_excel(xls, sheet_name=hoja_seleccionada)
                else:
                    df_crudo = pd.read_excel(xls)
            else:
                df_crudo = pd.read_csv(archivo_local)

            df_crudo.dropna(how='all', inplace=True)
            opciones_excel = list(df_crudo.columns)
            opciones_desplegable = [
                "[Omitir]", "[Escribir valor fijo manual]"] + opciones_excel

            st.markdown("### 💡 Asistente Inteligente de Columnas")
            st.info("El sistema emparejó tus columnas automáticamente. (La Vertiente ya se asignó automáticamente en la configuración previa).")

            cols = st.columns(4)
            mapeo_usuario = {}

            # Asignación oculta de la vertiente en el backend
            col_falsa_vertiente = "_fijo_Vertiente"
            df_crudo[col_falsa_vertiente] = vertiente_global
            mapeo_usuario["Vertiente"] = col_falsa_vertiente

            # SOLUCIÓN AL HUECO DE LA CUADRÍCULA:
            # Filtramos los campos visuales primero para que el iterador cuente 12 campos exactos (3x4)
            campos_visuales = [c for c in CAMPOS_OFICIALES if c != "Vertiente"]

            for idx, campo in enumerate(campos_visuales):
                with cols[idx % 4]:
                    nombre_amigable = campo.replace('_', ' ')
                    sugerencia = sugerir_mapeo(campo, opciones_excel)
                    idx_defecto = opciones_desplegable.index(
                        sugerencia) if sugerencia in opciones_desplegable else 0

                    seleccion = st.selectbox(
                        f"🔗 {nombre_amigable}", options=opciones_desplegable, index=idx_defecto, key=f"sel_{campo}")

                    if seleccion == "[Escribir valor fijo manual]":
                        val_manual = st.text_input(
                            f"✍️ Escribe el {nombre_amigable}:", key=f"man_{campo}")
                        if val_manual:
                            col_falsa = f"_fijo_{campo}"
                            df_crudo[col_falsa] = val_manual
                            mapeo_usuario[campo] = col_falsa
                        else:
                            mapeo_usuario[campo] = "[Omitir]"
                    else:
                        mapeo_usuario[campo] = seleccion

            st.markdown("---")
            if st.button("🔍 Revisar y Limpiar Datos", type="primary"):
                with st.spinner("Limpiando textos, quitando acentos y estructurando..."):
                    # Las condicionales lógicas ahora buscan la palabra "Diagnostico"
                    if "Diagnostico" in modulo_activo:
                        calificaciones, err = obtener_calificaciones()
                        if err:
                            st.error(
                                f"Error al conectar con calificaciones: {err}")
                        else:
                            v_25, v_16, anom = procesar_cruce_etl_sp(
                                df_crudo, mapeo_usuario, calificaciones)
                            st.session_state["df_validos"] = v_25
                            st.session_state["df_anomalias"] = anom
                            st.session_state["fase"] = 2
                            st.rerun()
                    else:
                        v_16, anom = procesar_ingesta_global(
                            df_crudo, mapeo_usuario)
                        st.session_state["df_validos"] = v_16
                        st.session_state["df_anomalias"] = anom
                        st.session_state["fase"] = 2
                        st.rerun()

    # ---------------------------------------------------------
    # PASO 2: RESUMEN, DESCARGA Y ACCIÓN FINAL
    # ---------------------------------------------------------
    elif st.session_state.get("fase") == 2:
        df_validos = st.session_state.get("df_validos", pd.DataFrame())
        df_anomalias = st.session_state.get("df_anomalias", pd.DataFrame())

        st.markdown("### 📊 Resumen de tu Archivo")
        m1, m2, m3 = st.columns(3)
        m1.metric("🟢 Alumnos listos", len(df_validos))
        m2.metric("⚠️ Casos para revisar", len(df_anomalias))

        if "Limpiador" in modulo_activo:
            m3.metric("⚙️ Entorno", "Modo Seguro (Local)")
        elif "Diagnostico" in modulo_activo:
            m3.metric("⚙️ Destino", "Base SP Oficial")
        else:
            m3.metric("⚙️ Destino", "Staging Area Global")

        st.markdown(f"<div class='panel-descarga'>", unsafe_allow_html=True)
        col_txt, col_btn = st.columns([2, 1])
        with col_txt:
            nombre_archivo = st.text_input(
                "Nombra tu archivo a descargar:", value="Archivo_INFOTEC_Limpio")
        with col_btn:
            st.write("")
            st.write("")
            excel_data = df_a_excel_multipestana(df_validos, df_anomalias)
            st.download_button("⬇️ Descargar Archivo Limpio", data=excel_data,
                               file_name=f"{nombre_archivo}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown("</div><br>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(
            ["✅ Datos Correctos (Limpios)", "⚠️ Corregir Errores (Editor en Vivo)"])

        with tab1:
            st.success(
                "Tus datos están perfectos. No tienen acentos, todo está en mayúsculas (excepto correos) y listos para uso oficial.")
            st.dataframe(df_validos, use_container_width=True)

        with tab2:
            st.warning(
                "Estos alumnos tienen problemas. **Haz doble clic en las celdas para corregirlos.**")
            anomalias_editadas = st.data_editor(
                df_anomalias, use_container_width=True, num_rows="dynamic")

        st.markdown("---")

        if "Limpiador" not in modulo_activo:
            st.markdown("### 🚀 Enviar a Base de Datos Institucional")
            etiqueta_boton = "🚨 ENVIAR A SERVIDORES PÚBLICOS" if "Diagnostico" in modulo_activo else "🚨 ENVIAR A BD GLOBAL"

            if st.button(etiqueta_boton, type="primary"):
                with st.spinner("Transmitiendo..."):
                    ruta_api = "aldo" if "Diagnostico" in modulo_activo else "global"
                    ins_b, ins_a, dup, err = inyectar_datos_limpios(
                        df_validos, anomalias_editadas, ruta=ruta_api)

                    if err:
                        st.error(f"❌ Error de red: {err}")
                    else:
                        st.success(
                            f"✅ ¡Guardado Exitoso! {ins_b} registros añadidos.")
                        if ins_a > 0:
                            st.warning(
                                f"⚠️ {ins_a} registros pasaron a revisión.")
                        st.balloons()
