import streamlit as st
import pandas as pd
from core_processing import limpiar_datos, aplicar_mapeo_estatico
from google_sync import conectar_sheets, sincronizar_datos_seguro

st.set_page_config(page_title="Sincronizador EPC",
                   layout="wide", initial_sidebar_state="collapsed")

# =====================================================================
# 🔒 SISTEMA DE CONTROL DE ACCESO (GATEKEEPER)
# =====================================================================

def check_password():
    """Devuelve True si el usuario ingresó la contraseña correcta."""
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return True

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown("<div style='text-align: center;'>",
                    unsafe_allow_html=True)

        st.image("logo.png", width=180)

        st.markdown(
            "<h2 style='color: #1F4E78; font-weight: 900;'>Acceso Institucional</h2>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color: #64748b; margin-bottom: 2rem;'>Sincronizador EPC - Control Escolar</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("login_form"):
            password_ingresada = st.text_input(
                "Clave de Administrador", type="password", placeholder="••••••••")
            submitted = st.form_submit_button(
                "Desbloquear Sistema", use_container_width=True, type="primary")

            if submitted:
                if password_ingresada.strip() == st.secrets["access_control"]["admin_password"]:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas.")

    return False

# =====================================================================
# 🚀 FLUJO PRINCIPAL PROTEGIDO (UX/UI REDISEÑADA)
# =====================================================================
if check_password():

    # Encabezado Minimalista
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #1F4E78; font-weight: 900;'>Sincronizador EPC</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.1rem;'>Motor de Inyección de Solicitantes a BD Maestra</p>", unsafe_allow_html=True)
    st.markdown("<hr style='border: 1px solid #e2e8f0; width: 50%; margin: 2rem auto;'>",
                unsafe_allow_html=True)

    # Contenedor central para el flujo de trabajo
    col_izq, col_centro, col_der = st.columns([1, 1.5, 1])

    with col_centro:
        # 1. Zona de Carga Amigable
        archivo = st.file_uploader(
            "Selecciona o arrastra el reporte exportado de Forminator",
            type=['xlsx', 'csv'],
            help="El sistema procesará automáticamente las columnas y omitirá los registros duplicados."
        )

        if archivo:
            # 2. Feedback rápido y limpio
            df = pd.read_csv(archivo) if archivo.name.endswith(
                '.csv') else pd.read_excel(archivo)

            st.markdown(f"""
            <div style='background-color: #f0fdf4; border-left: 4px solid #16a34a; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem;'>
                <p style='color: #166534; margin: 0; font-weight: 600;'>✅ Archivo reconocido correctamente</p>
                <p style='color: #15803d; margin: 0; font-size: 0.9rem;'>{archivo.name} — <strong>{len(df)} registros detectados</strong></p>
            </div>
            <br>
            """, unsafe_allow_html=True)

            # 3. Botón de Acción Principal
            if st.button("🚀 Iniciar Inyección en la Nube", type="primary", use_container_width=True):

                # 4. Estado de progreso dinámico
                with st.status("Procesando lote de datos...", expanded=True) as status:

                    st.write("Conectando con Google Workspace API...")
                    cliente = conectar_sheets()

                    if cliente:
                        st.write("Limpiando formatos y mapeando esquema...")
                        df_limpio = limpiar_datos(df)
                        df_mapeado = aplicar_mapeo_estatico(df_limpio)

                        st.write("Comparando matrices e inyectando filas nuevas...")

                        # 4. Única inyección para evitar el error de doble bloque
                        actualizados_maestra, insertados_anomalias = sincronizar_datos_seguro(
                            cliente=cliente,
                            id_documento="1okof2eOnIif-JJhaMqUQspx5Q8Pc9-z7N2UmkLt90XA",
                            nombre_hoja="BD_Maestra_Solicitantes",
                            df_nuevo=df_mapeado
                        )

                        # 5. Cierre y resultados limpios contemplando ambos escenarios
                        if actualizados_maestra > 0 or insertados_anomalias > 0:
                            status.update(
                                label=f"¡Éxito! ({actualizados_maestra} actualizados, {insertados_anomalias} anomalías)",
                                state="complete", expanded=False
                            )
                            st.balloons()

                            if actualizados_maestra > 0:
                                st.success(
                                    f"✅ Se rellenaron los datos de {actualizados_maestra} expedientes en la Base Maestra.")

                            if insertados_anomalias > 0:
                                st.warning(
                                    f"⚠️ Se detectaron {insertados_anomalias} aspirantes en Forminator que NO realizaron el examen. Fueron trasladados a 'Casos_Extraordinarios_Curp'.")
                        else:
                            status.update(
                                label="Sincronización Completada (Cero cambios)",
                                state="complete", expanded=False
                            )
                            st.info(
                                "No se actualizó información. Todos los perfiles detectados ya estaban sincronizados previamente.")