# ============================================================================
# ARCHIVO: core_processing.py
# ============================================================================
import pandas as pd
import unicodedata

# Diccionario estricto: De Forminator crudo -> BD Maestra Solicitantes
DICCIONARIO_MAESTRA = {
    'Submission Time': 'Marca Temporal (Forminator)',
    'CURP': 'CURP',
    'Nombre(s)': 'Nombre(s)',
    'Primer apellido': 'Apellido Paterno',
    'Segundo apellido': 'Apellido Materno',
    'Correo institucional': 'Correo Electrónico',
    'Sexo': 'Género',
    '¿Cuál es tu edad al momento de postulación?': 'Edad',
    'Estado': 'Estado de la República',
    '¿Cuál es el nombre de la dependencia de gobierno donde laboras?': 'Dependencia de Gobierno',
    '¿Cuál es el cargo que desempeñas?': 'Área de Adscripción / Cargo',
}

COLUMNAS_OFICIALES = [
    "Marca Temporal (Forminator)", "CURP", "Nombre(s)", "Apellido Paterno", "Apellido Materno",
    "Nombre Completo", "Correo Electrónico", "Género", "Edad", "Estado de la República",
    "Dependencia de Gobierno", "Área de Adscripción / Cargo",
    "Fecha del examen",
    "Puntaje B1", "Puntaje B2", "Puntaje B3", "Puntaje B4", "Puntaje B5", "Puntaje B6", "Puntaje Global",
    "Módulo Sugerido", "Módulo Elegido", "Vertiente", "Estatus", "Generación", "Alerta de Identidad"
]


def limpiar_datos(df):
    """Normaliza encabezados, remueve duplicados y limpia strings (Eliminando acentos)."""
    df.columns = df.columns.str.strip()

    # Eliminación de duplicados locales
    if 'CURP' in df.columns:
        df = df.drop_duplicates(subset=['CURP'], keep='last')
        df['CURP'] = df['CURP'].astype(str).str.strip().str.upper()

    # Sanitización masiva de strings (Eliminación de Tildes/Acentos, Todo a Mayúsculas)
    # 3. Sanitización masiva de strings (Eliminación de Tildes/Acentos, Todo a Mayúsculas)
    cols_object = df.select_dtypes(include=['object', 'string']).columns
    for col in cols_object:
        # Se agrega str(x) dentro de lambda para evitar el TypeError con valores NaN/Float
        df[col] = df[col].astype(str).apply(
            lambda x: unicodedata.normalize('NFKD', str(x)).encode(
                'ASCII', 'ignore').decode('utf-8')
        )
        df[col] = df[col].str.upper().str.strip()
        df[col] = df[col].replace('NAN', '')
        # También limpiamos la versión sin mayúsculas por si acaso
        df[col] = df[col].replace('nan', '')

    # EXCEPCIÓN: Correo a minúsculas
    if 'Correo institucional' in df.columns:
        df['Correo institucional'] = df['Correo institucional'].astype(
            str).str.strip().str.lower()
        df['Correo institucional'] = df['Correo institucional'].replace(
            'nan', '')

    return df


def aplicar_mapeo_estatico(df_limpio):
    """Traduce los encabezados de Forminator y estructura la matriz geométrica de 26 columnas."""
    df_procesado = pd.DataFrame()

    for col_forminator, col_oficial in DICCIONARIO_MAESTRA.items():
        if col_forminator in df_limpio.columns:
            df_procesado[col_oficial] = df_limpio[col_forminator]
        else:
            df_procesado[col_oficial] = ''

    # Construir 'Nombre Completo' automáticamente (Si faltan columnas, no se rompe)
    cols_nombre = [c for c in [
        'Nombre(s)', 'Apellido Paterno', 'Apellido Materno'] if c in df_procesado.columns]
    if cols_nombre:
        df_procesado['Nombre Completo'] = df_procesado[cols_nombre].fillna(
            '').agg(' '.join, axis=1)
        df_procesado['Nombre Completo'] = df_procesado['Nombre Completo'].str.replace(
            r'\s+', ' ', regex=True).str.strip()

    # Inyección de Campos por Defecto y Vacíos para el Examen
    df_procesado['Vertiente'] = 'SP'
    df_procesado['Estatus'] = 'Solicitante'
    df_procesado['Generación'] = ''

    columnas_examen = [
        "Fecha del examen", "Puntaje B1", "Puntaje B2", "Puntaje B3",
        "Puntaje B4", "Puntaje B5", "Puntaje B6", "Puntaje Global",
        "Módulo Sugerido", "Módulo Elegido"
    ]
    for col in columnas_examen:
        df_procesado[col] = ''

    df_procesado['Alerta de Identidad'] = ''

    return df_procesado
