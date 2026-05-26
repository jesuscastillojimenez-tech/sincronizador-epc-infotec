# Plan Maestro: Sistema Local de Homologación e Identidad Única (EPC)

Este sistema web migra la gestión fragmentada de la Escuela Pública de Código hacia una arquitectura centralizada de **Tabla Plana**, eliminando el desorden de las múltiples pestañas de generaciones y resolviendo las duplicidades de reingreso de forma segura y local en cumplimiento con la LGPDPPSO en México.

---

## 1. Arquitectura de Archivos
- `app.py` -> Interfaz gráfica de usuario con Streamlit (Módulo de arrastre Drag & Drop).
- `core_processing.py` -> Funciones offline de normalización de cadenas de texto y algoritmo de coincidencia difusa (Fuzzy Matching).
- `google_sync.py` -> Orquestador de lectura, verificación de existencia por llave primaria (CURP) y actualización matricial en Google Sheets vía `gspread`.

---

## 2. Flujo Lógico Mejorado (Evitar Duplicados)

### A. Extracción y Limpieza Local (Pandas)
1. El coordinador arrastra el archivo `.xlsx` de Forminator en la UI de Streamlit.
2. Pandas procesa el archivo en la memoria RAM del servidor local.
3. Se normalizan los encabezados (eliminación de espacios, conversión a mayúsculas).

### B. Mapeo Dinámico de Columnas (Fuzzy Matching Offline)
1. Leer los encabezados oficiales de la Fila 1 de la hoja destino en la nube.
2. Comparar de forma puramente matemática los encabezados del archivo cargado contra los oficiales usando `difflib.get_close_matches`.
3. Renombrar las columnas del DataFrame de entrada para alinearlas con la estructura oficial de la base maestra.

### C. Inyección Inteligente (Verificación de Llave Primaria)
Para corregir el desorden en el que un alumno aparece registrado múltiples veces al reingresar, el backend implementará la siguiente lógica antes de subir los datos:
1. Descargar la columna completa de `CURP` de la hoja de Google Sheets.
2. Comparar las CURPs del archivo nuevo contra las existentes en la nube:
   - **Si la CURP NO existe**: Se prepara el registro completo del alumno como una nueva fila y se añade al lote de inserción masiva (`append_rows`).
   - **Si la CURP SÍ existe**: Se localiza el número de fila exacto en Google Sheets y se realiza una actualización dirigida (`update_cells`) para modificar únicamente el `ESTATUS ALUMNO`, `GRUPO` y `FECHA DE ACTUALIZACION`, conservando su historial previo y evitando duplicar la persona.

---

## 3. Especificaciones de Hojas Destino (Estructura Maestra)

### Destino 1: `Base de Datos Maestra` (Pestaña: "Respuestas formulario")
- Encabezados clave a mantener alineados: Marca temporal, Estado:, Alcaldía o Municipio:, Código Postal, CURP, Nombre de la Dependencia, Nombre (s), Apellidos, Edad, Correo electrónico.
