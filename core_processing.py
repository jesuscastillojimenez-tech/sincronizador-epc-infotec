import pandas as pd
import uuid
import hashlib
from datetime import datetime, date
import re
import unicodedata

# ==========================================
# SCHEMA ESTRUCTURAL UNIVERSAL (13 Columnas Mínimas)
# ==========================================
CAMPOS_OFICIALES = [
    "Marca_Temporal", "CURP", "Nombre", "Apellido_Paterno",
    "Apellido_Materno", "Correo_Electronico", "Genero",
    "Estado_Republica", "Dependencia_Gobierno", "Area_Adscripcion_Cargo",
    "Vertiente", "Estatus", "Curso_Asignado"
]

# Catálogo RENAPO para Enriquecimiento Biológico de Datos
CATALOGO_ESTADOS = {
    'AS': 'AGUASCALIENTES', 'BC': 'BAJA CALIFORNIA', 'BS': 'BAJA CALIFORNIA SUR',
    'CC': 'CAMPECHE', 'CL': 'COAHUILA', 'CM': 'COLIMA', 'CS': 'CHIAPAS',
    'CH': 'CHIHUAHUA', 'DF': 'CIUDAD DE MEXICO', 'DG': 'DURANGO',
    'GT': 'GUANAJUATO', 'GR': 'GUERRERO', 'HG': 'HIDALGO', 'JC': 'JALISCO',
    'MC': 'ESTADO DE MEXICO', 'MN': 'MICHOACAN', 'MS': 'MORELOS',
    'NT': 'NAYARIT', 'NL': 'NUEVO LEON', 'OC': 'OAXACA', 'PL': 'PUEBLA',
    'QT': 'QUERETARO', 'QR': 'QUINTANA ROO', 'SP': 'SAN LUIS POTOSI',
    'SL': 'SINALOA', 'SR': 'SONORA', 'TC': 'TABASCO', 'TS': 'TAMAULIPAS',
    'TL': 'TLAXCALA', 'VZ': 'VERACRUZ', 'YN': 'YUCATAN', 'ZS': 'ZACATECAS', 'NE': 'NACIDO EN EL EXTRANJERO'
}

# ==========================================
# FUNCIONES DE SANITIZACIÓN Y ENRIQUECIMIENTO
# ==========================================


def limpiar_texto(texto, formato="upper"):
    """
    Filtro de Sanitización Estética Universal: 
    Quita acentos, elimina espacios extra y convierte a MAYÚSCULAS (por defecto).
    """
    if pd.isna(texto):
        return ""
    texto_limpio = str(texto).strip()

    # Eliminar múltiples espacios internos accidentalmente tecleados por el usuario
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

    # Magia de Unicodedata: Separa letras de sus acentos y elimina los acentos
    texto_limpio = ''.join(c for c in unicodedata.normalize(
        'NFD', texto_limpio) if unicodedata.category(c) != 'Mn')

    if formato == "lower":
        return texto_limpio.lower()

    # El estándar institucional ahora es todo en mayúsculas
    return texto_limpio.upper()


def extraer_datos_biologicos(curp):
    """Magia de Datos: Extrae Edad, Género y Estado desde la estructura de la CURP."""
    curp = limpiar_texto(curp, "upper")
    if len(curp) != 18 or not curp[4:10].isdigit():
        return "", "", "", ""

    # 1. Extracción de Edad y Fecha de Nacimiento (Fórmula Y2K)
    año_str, mes_str, dia_str = curp[4:6], curp[6:8], curp[8:10]
    caracter_17 = curp[16]
    siglo = "19" if caracter_17.isdigit() else "20"
    año_completo = int(siglo + año_str)

    try:
        fecha_nac_obj = date(año_completo, int(mes_str), int(dia_str))
        hoy = date.today()
        edad = str(hoy.year - fecha_nac_obj.year - ((hoy.month, hoy.day)
                   < (fecha_nac_obj.month, fecha_nac_obj.day)))
        fecha_nac = fecha_nac_obj.strftime("%Y-%m-%d")
    except:
        fecha_nac, edad = "", ""

    # 2. Extracción de Género (Posición 11: H o M)
    genero_letra = curp[10]
    genero = "HOMBRE" if genero_letra == 'H' else "MUJER" if genero_letra == 'M' else ""

    # 3. Extracción de Entidad Federativa (Posiciones 12 y 13)
    estado_codigo = curp[11:13]
    estado = CATALOGO_ESTADOS.get(estado_codigo, "")

    return fecha_nac, edad, genero, estado


def generar_id_determinista(curp, curso, correo=""):
    """
    Generador de Llave Primaria Compuesta (ID_EPC).
    Fusiona Identidad (CURP o Correo) + Transacción (Curso) en un Hash único.
    """
    curp_limpia = limpiar_texto(curp, "upper")
    correo_limpio = limpiar_texto(correo, "lower")
    curso_limpio = limpiar_texto(curso, "upper")

    base_identidad = ""
    # Prioridad 1: CURP Oficial
    if curp_limpia and len(curp_limpia) == 18:
        base_identidad = curp_limpia
    # Prioridad 2 (Respaldo): Correo Electrónico
    elif correo_limpio:
        base_identidad = correo_limpio

    if base_identidad:
        llave_compuesta = f"{base_identidad}|{curso_limpio}"
        hash_obj = hashlib.md5(llave_compuesta.encode('utf-8'))
        return f"EPC-{hash_obj.hexdigest()[:10].upper()}"

    # Fallback crítico si no hay ni CURP ni Correo
    return f"INC-{uuid.uuid4().hex[:8].upper()}"

# ==========================================
# MÓDULO 1: SERVIDORES PÚBLICOS (CRUCE CON EXAMEN)
# ==========================================


def procesar_cruce_etl_sp(df_crudo, mapeo_visual, calificaciones_json):
    """Genera 3 DataFrames: Validos SP (26 col), Validos Global (17 col) y Anomalías."""
    df_temp = pd.DataFrame()

    # Construcción inicial usando el mapeo del frontend
    for campo_oficial, col_excel in mapeo_visual.items():
        df_temp[campo_oficial] = df_crudo[col_excel] if col_excel != "[Omitir]" else ""

    # 🧹 EXTERMINADOR QUIRÚRGICO DE FILAS FANTASMAS
    df_temp['filtro_nombre'] = df_temp['Nombre'].apply(
        lambda x: limpiar_texto(x, "upper"))
    df_temp['filtro_correo'] = df_temp['Correo_Electronico'].apply(
        lambda x: limpiar_texto(x, "upper"))
    df_temp = df_temp[~((df_temp['filtro_nombre'] == '') &
                        (df_temp['filtro_correo'] == ''))].copy()
    df_temp.drop(columns=['filtro_nombre', 'filtro_correo'], inplace=True)

    df_temp['CURP'] = df_temp['CURP'].apply(
        lambda x: limpiar_texto(x, "upper"))

    # Cruce (Merge) con Calificaciones
    df_examenes = pd.DataFrame(calificaciones_json)
    if not df_examenes.empty and 'CURP' in df_examenes.columns:
        df_examenes['CURP'] = df_examenes['CURP'].apply(
            lambda x: limpiar_texto(x, "upper"))
    else:
        df_examenes = pd.DataFrame(columns=['CURP'])

    df_merged = pd.merge(df_temp, df_examenes, on='CURP',
                         how='left', suffixes=('_excel', '_examen'))

    validos_sp = []
    validos_global = []
    anomalias = []

    for index, row in df_merged.iterrows():
        # Formateo Automático a MAYÚSCULAS SIN ACENTOS
        nombre = limpiar_texto(row.get('Nombre', ''), "upper")
        paterno = limpiar_texto(row.get('Apellido_Paterno', ''), "upper")
        materno = limpiar_texto(row.get('Apellido_Materno', ''), "upper")
        nombre_comp = f"{nombre} {paterno} {materno}".strip()

        curp = row.get('CURP', '')
        curso_asignado = limpiar_texto(row.get('Curso_Asignado', ''), "upper")

        # 🛡️ Regla "Golden Record" para el Correo (El examen manda - Minúsculas estrictas)
        correo_excel = limpiar_texto(
            row.get('Correo_Electronico_excel', row.get('Correo_Electronico', '')), "lower")
        correo_examen = limpiar_texto(
            row.get('Correo_Electronico_examen', ''), "lower")
        correo_final = correo_examen if correo_examen else correo_excel

        # FILTROS DE CALIDAD (Envío a Cuarentena)
        if not correo_final:
            anomalias.append({"ID_Incidente": f"INC-{uuid.uuid4().hex[:6].upper()}", "CURP_Conflicto": curp,
                             "Tipo_Anomalia": "FALTA CORREO ELECTRONICO", "Nombre_Solicitante": nombre_comp, "Estatus_Resolucion": "PENDIENTE"})
            continue
        if len(curp) != 18 or not curp.isalnum():
            anomalias.append({"ID_Incidente": f"INC-{uuid.uuid4().hex[:6].upper()}", "CURP_Conflicto": curp,
                             "Tipo_Anomalia": "CURP INCOMPLETA O INVALIDA", "Nombre_Solicitante": nombre_comp, "Estatus_Resolucion": "PENDIENTE"})
            continue
        if pd.isna(row.get('Puntaje_Global')) or str(row.get('Puntaje_Global')) == "":
            anomalias.append({"ID_Incidente": f"INC-{uuid.uuid4().hex[:6].upper()}", "CURP_Conflicto": curp,
                             "Tipo_Anomalia": "NO REALIZO EXAMEN DIAGNOSTICO", "Nombre_Solicitante": nombre_comp, "Estatus_Resolucion": "PENDIENTE"})
            continue

        # Enriquecimiento y Empaquetado
        fecha_nac, edad_calc, genero_calc, estado_calc = extraer_datos_biologicos(
            curp)

        genero_final = limpiar_texto(
            row.get('Genero', ''), "upper") or genero_calc
        estado_final = limpiar_texto(
            row.get('Estado_Republica', ''), "upper") or estado_calc
        id_maestro = generar_id_determinista(
            curp, curso_asignado, correo_final)

        marca_temp_limpia = str(
            row.get('Marca_Temporal_excel', row.get('Marca_Temporal', '')))
        fecha_examen_limpia = str(row.get('Marca_Temporal_examen', ''))
        vertiente = limpiar_texto(row.get('Vertiente', ''), "upper")
        estatus = limpiar_texto(row.get('Estatus', ''), "upper")

        # EMPAQUETADO ODS ALDO (26 Columnas)
        validos_sp.append({
            "ID_EPC": id_maestro, "Marca_Temporal": marca_temp_limpia, "CURP": curp,
            "Nombre": nombre, "Apellido_Paterno": paterno, "Apellido_Materno": materno,
            "Nombre_Completo": nombre_comp, "Correo_Electronico": correo_final, "Genero": genero_final,
            "Fecha_Nacimiento": fecha_nac, "Edad_Inscripcion": edad_calc,
            "Estado_Republica": estado_final, "Dependencia_Gobierno": limpiar_texto(row.get('Dependencia_Gobierno', ''), "upper"),
            "Area_Adscripcion_Cargo": limpiar_texto(row.get('Area_Adscripcion_Cargo', ''), "upper"),
            "Fecha_Examen": fecha_examen_limpia,
            "Puntaje_B1": row.get('B1', ''), "Puntaje_B2": row.get('B2', ''), "Puntaje_B3": row.get('B3', ''),
            "Puntaje_B4": row.get('B4', ''), "Puntaje_B5": row.get('B5', ''), "Puntaje_B6": row.get('B6', ''),
            "Puntaje_Global": row.get('Puntaje_Global', ''),
            "Modulo_Sugerido": limpiar_texto(row.get('Modulo_Sugerido', row.get('Modulo_Asignado', '')), "upper"),
            "Curso_Asignado": curso_asignado, "Vertiente": vertiente, "Estatus": estatus
        })

        # EMPAQUETADO GLOBAL (17 Columnas)
        validos_global.append({
            "ID_EPC": id_maestro, "Marca_Temporal": marca_temp_limpia, "CURP": curp,
            "Nombre": nombre, "Apellido_Paterno": paterno, "Apellido_Materno": materno,
            "Nombre_Completo": nombre_comp, "Correo_Electronico": correo_final, "Genero": genero_final,
            "Fecha_Nacimiento": fecha_nac, "Edad_Inscripcion": edad_calc,
            "Estado_Republica": estado_final, "Dependencia_Gobierno": limpiar_texto(row.get('Dependencia_Gobierno', ''), "upper"),
            "Area_Adscripcion_Cargo": limpiar_texto(row.get('Area_Adscripcion_Cargo', ''), "upper"),
            "Curso_Asignado": curso_asignado, "Vertiente": vertiente, "Estatus": estatus
        })

    return pd.DataFrame(validos_sp), pd.DataFrame(validos_global), pd.DataFrame(anomalias)

# ==========================================
# MÓDULO 2: INGESTA UNIVERSAL Y LIMPIADOR
# ==========================================


def procesar_ingesta_global(df_crudo, mapeo_visual):
    """Procesamiento Limpio Universal: Retorna 17 Columnas y Cuarentena."""
    df_temp = pd.DataFrame()
    for campo_oficial, col_excel in mapeo_visual.items():
        df_temp[campo_oficial] = df_crudo[col_excel] if col_excel != "[Omitir]" else ""

    # 🧹 EXTERMINADOR QUIRÚRGICO DE FILAS FANTASMAS
    df_temp['filtro_nombre'] = df_temp['Nombre'].apply(
        lambda x: limpiar_texto(x, "upper"))
    df_temp['filtro_correo'] = df_temp['Correo_Electronico'].apply(
        lambda x: limpiar_texto(x, "lower"))
    df_temp = df_temp[~((df_temp['filtro_nombre'] == '') &
                        (df_temp['filtro_correo'] == ''))].copy()
    df_temp.drop(columns=['filtro_nombre', 'filtro_correo'], inplace=True)

    df_temp['CURP'] = df_temp['CURP'].apply(
        lambda x: limpiar_texto(x, "upper"))

    validos_global = []
    anomalias = []

    for index, row in df_temp.iterrows():
        nombre = limpiar_texto(row.get('Nombre', ''), "upper")
        paterno = limpiar_texto(row.get('Apellido_Paterno', ''), "upper")
        materno = limpiar_texto(row.get('Apellido_Materno', ''), "upper")
        nombre_comp = f"{nombre} {paterno} {materno}".strip()

        curp = row.get('CURP', '')
        correo = limpiar_texto(row.get('Correo_Electronico', ''), "lower")
        curso_asignado = limpiar_texto(row.get('Curso_Asignado', ''), "upper")

        # Filtro relajado (Tolera falta de CURP, pero NO tolera falta de Correo)
        if not correo or (len(curp) != 18 and curp != ""):
            anomalias.append({"ID_Incidente": f"INC-{uuid.uuid4().hex[:6].upper()}", "CURP_Conflicto": curp,
                             "Tipo_Anomalia": "DATOS INCOMPLETOS O INVALIDOS", "Nombre_Solicitante": nombre_comp, "Estatus_Resolucion": "PENDIENTE"})
            continue

        fecha_nac, edad_calc, genero_calc, estado_calc = extraer_datos_biologicos(
            curp) if curp else ("", "", "", "")

        genero_final = limpiar_texto(
            row.get('Genero', ''), "upper") or genero_calc
        estado_final = limpiar_texto(
            row.get('Estado_Republica', ''), "upper") or estado_calc

        id_maestro = generar_id_determinista(curp, curso_asignado, correo)

        marca_temp_limpia = str(row.get('Marca_Temporal', ''))
        vertiente = limpiar_texto(row.get('Vertiente', ''), "upper")
        estatus = limpiar_texto(row.get('Estatus', ''), "upper")

        validos_global.append({
            "ID_EPC": id_maestro, "Marca_Temporal": marca_temp_limpia, "CURP": curp,
            "Nombre": nombre, "Apellido_Paterno": paterno, "Apellido_Materno": materno,
            "Nombre_Completo": nombre_comp, "Correo_Electronico": correo, "Genero": genero_final,
            "Fecha_Nacimiento": fecha_nac, "Edad_Inscripcion": edad_calc,
            "Estado_Republica": estado_final, "Dependencia_Gobierno": limpiar_texto(row.get('Dependencia_Gobierno', ''), "upper"),
            "Area_Adscripcion_Cargo": limpiar_texto(row.get('Area_Adscripcion_Cargo', ''), "upper"),
            "Curso_Asignado": curso_asignado, "Vertiente": vertiente, "Estatus": estatus
        })

    return pd.DataFrame(validos_global), pd.DataFrame(anomalias)
