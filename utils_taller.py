import streamlit as st
import json
import tempfile
import pandas as pd
import io
import re
import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build

# === Google Services Setup ===
with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
    json.dump(json.loads(st.secrets["SERVICE_ACCOUNT_JSON"]), f)
    SERVICE_ACCOUNT_FILE = f.name

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
docs_service = build("docs", "v1", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)
sheets_service = build("sheets", "v4", credentials=creds)

TEMPLATE_ID = "1I2jMQ1IjmG6_22dC7u6LYQfQzlND4WIvEusd756LFuo"

# === Gemini API ===
def call_gemini(prompt: str) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": st.secrets["GEMINI_API_KEY"]}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 3000
        }
    }

    response = requests.post(url, headers=headers, params=params, json=data)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        st.error(f"Error en API Gemini: {response.status_code} - {response.text}")
        raise Exception("Fallo la llamada a Gemini con API Key.")

# === Prompting y generación de datos del curso ===
@st.cache_data(show_spinner=False)
def generar_datos_generales(nombre_del_taller, nivel, publico, student_persona, industria, objetivos_raw, horas):  
    prompt = f"""
    Eres diseñador instruccional senior en talleres de IA, Ciencia de Datos y Negocios, aplicando los principios de LearnLM, y los principios de la ciencia del aprendizaje
    para crear experiencias educativas efectivas y atractivas. Tu objetivo es generar un syllabus y outline
    que fomenten el aprendizaje activo, gestionen la carga cognitiva del estudiante y adapten el contenido
    a sus necesidades, inspirando curiosidad y profundizando la metacognición.

    Para generar los tres objetivos secundarios y sus descripciones: Genera TRES objetivos secundarios del curso.

    Formato:
    - titulo_primer_objetivo_secundario  = **máx. 6 palabras**
    - descripcion_primer_objetivo_secundario = **una frase ≤ 15 palabras**
    (repite para los tres objetivos)


    Con base en los siguientes datos:
    - Taller: {nombre_del_taller}
    - Nivel: {nivel}
    - Público objetivo: {publico}
    - Perfil base del estudiante: {student_persona}
    - Objetivos iniciales: {objetivos_raw}
    - Industria a la que va dirigida el taller: {industria}
    - Tiempo de duración del taller en horas: {horas}

    Devuélveme lo siguiente, separado por etiquetas:

    [PERFIL_INGRESO]
    ...
    [OBJETIVOS]
    ...
    [PERFIL_EGRESO]
    ...
    [DISTRIBUCION_HORAS]
    ...
    [OUTLINE]
    ...

    [TITULO_PRIMER_OBJETIVO_SECUNDARIO]
    ...

    [DESCRIPCION_PRIMER_OBJETIVO_SECUNDARIO]
    ...

    [TITULO_SEGUNDO_OBJETIVO_SECUNDARIO]
    ...

    [DESCRIPCION_SEGUNDO_OBJETIVO_SECUNDARIO]
    ...

    [TITULO_TERCER_OBJETIVO_SECUNDARIO]
    ...

    [DESCRIPCION_TERCER_OBJETIVO_SECUNDARIO]
    ...

    El outline debe generarse en Markdown con 1 FILA POR HORA.

    ### Reglas de distribución
    - **Cada sesión dura exactamente 1 hora** (no combines temas en bloques de 2 h).
    - Si `horas_totales` ≤ 4 → todo se imparte en **Día 1**.
    - Si `horas_totales` > 4 → reparte la mitad de sesiones en **Día 1** y la otra mitad en **Día 2**
    (redondea hacia arriba si es impar; p.ej. 7 h → 4 + 3).

    Incluye estas columnas:  
    | Sesión | Día | Título | Conceptos clave | Objetivo 1 | Objetivo 2 | Objetivo 3 | Descripción |


    """
    respuesta = call_gemini(prompt)

    def extraer(etiqueta):
        patron = rf"\[{etiqueta}\]\n(.*?)(?=\[|\Z)"
        r = re.search(patron, respuesta, re.DOTALL)
        return r.group(1).strip() if r else ""

    perfil_ingreso = extraer("PERFIL_INGRESO")
    objetivos = extraer("OBJETIVOS")
    perfil_egreso = extraer("PERFIL_EGRESO")
    outline = extraer("OUTLINE")

    # Nuevos campos: objetivos secundarios
    titulo1 = extraer("TITULO_PRIMER_OBJETIVO_SECUNDARIO")
    desc1 = extraer("DESCRIPCION_PRIMER_OBJETIVO_SECUNDARIO")
    titulo2 = extraer("TITULO_SEGUNDO_OBJETIVO_SECUNDARIO")
    desc2 = extraer("DESCRIPCION_SEGUNDO_OBJETIVO_SECUNDARIO")
    titulo3 = extraer("TITULO_TERCER_OBJETIVO_SECUNDARIO")
    desc3 = extraer("DESCRIPCION_TERCER_OBJETIVO_SECUNDARIO")

    return perfil_ingreso, objetivos, perfil_egreso, outline, titulo1, desc1, titulo2, desc2, titulo3, desc3

# === Placeholder replacement ===
def replace_placeholder(document_id, placeholder, new_text):
    requests = [{
        "replaceAllText": {
            "containsText": {"text": placeholder, "matchCase": True},
            "replaceText": new_text
        }
    }]
    docs_service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()

# === Generación del syllabus usando objetivos directamente ===
def generar_syllabus_completo(nombre_del_taller, nivel, objetivos_mejorados, publico, industria,
                               perfil_ingreso, perfil_egreso, outline,
                               titulo1, desc1, titulo2, desc2, titulo3, desc3):
    anio = 2025

    def pedir_seccion(etiqueta, instruccion):
        prompt = f"""
              Eres diseñador instruccional senior en talleres de IA, Ciencia de Datos y Negocios, aplicando los principios de LearnLM, genera el siguiente contenido:

                Curso: {nombre_del_taller}
                Año: {anio}
                Nivel: {nivel}
                Objetivos: {objetivos_mejorados}
                Perfil de ingreso: {perfil_ingreso}
                Perfil de egreso: {perfil_egreso}
                Outline:
                {outline}

                Devuelve únicamente el contenido para la sección: [{etiqueta}]
                {instruccion}
                """
        respuesta = call_gemini(prompt)
        return respuesta.strip()

    generalidades = pedir_seccion("Redacta un párrafo breve que combine descripción general del curso, su objetivo, el perfil de egreso, la duración del taller y entragables del taller.")
    ingreso = pedir_seccion("PERFIL_INGRESO", "Redacta un párrafo claro y directo del perfil de ingreso del estudiante ya sea por roles sugeridos de la industria o por equipos de trabajo.")
    detalles = pedir_seccion("Escribe la lista de de las sesiones por hora a tocar, esto dependerá de cuántas horas pongan en el input, cada una con título y una breve descripción, NO usar negritas en markdown.")

    template_copy = drive_service.files().copy(
        fileId=TEMPLATE_ID,
        body={"name": f"Syllabus - {nombre_del_taller}"}
    ).execute()
    document_id = template_copy["id"]

    replace_placeholder(document_id, "{{nombre_del_curso}}", nombre_del_taller)
    replace_placeholder(document_id, "{{anio}}", str(anio))
    replace_placeholder(document_id, "{{generalidades_del_programa}}", generalidades)
    replace_placeholder(document_id, "{{perfil_ingreso}}", ingreso)
    replace_placeholder(document_id, "{{detalles_plan_estudios}}", detalles)

    replace_placeholder(document_id, "{{titulo_primer_objetivo_secundario}}", titulo1)
    replace_placeholder(document_id, "{{descripcion_primer_objetivo_secundario}}", desc1)
    replace_placeholder(document_id, "{{titulo_segundo_objetivo_secundario}}", titulo2)
    replace_placeholder(document_id, "{{descripcion_segundo_objetivo_secundario}}", desc2)
    replace_placeholder(document_id, "{{titulo_tercer_objetivo_secundario}}", titulo3)
    replace_placeholder(document_id, "{{descripcion_tercer_objetivo_secundario}}", desc3)

    drive_service.permissions().create(
        fileId=document_id,
        body={"type": "domain", "role": "writer", "domain": "datarebels.mx"},
        fields="id"
    ).execute()

    return f"https://docs.google.com/document/d/{document_id}/edit"

