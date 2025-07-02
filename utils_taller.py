import os
import re
import tempfile
import datetime
import requests
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

"""utils_taller.py – Generador de syllabus para *talleres*
---------------------------------------------------------------------
Versión mejorada: el prompt solicita textos más "nutridos" para
  • Generalidades del programa
  • Perfil de ingreso
  • Descripción y Detalles del plan de estudios (viñetas)
Sigue la misma lógica y placeholders que el generador de cursos.
"""

# --------------------------------------------------------------------------- #
#  Configuración de servicios Google                                          #
# --------------------------------------------------------------------------- #
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp:
    tmp.write(st.secrets["SERVICE_ACCOUNT_JSON"])
    SERVICE_KEY = tmp.name

creds = service_account.Credentials.from_service_account_file(
    SERVICE_KEY, scopes=SCOPES
)

docs_service = build("docs", "v1", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)

# --------------------------------------------------------------------------- #
#  Llamada a Gemini‑1.5‑Flash                                                 #
# --------------------------------------------------------------------------- #

def call_gemini(prompt: str) -> str:
    """Devuelve la respuesta textual de Gemini 1.5 Flash."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
    )
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        params={"key": st.secrets["GEMINI_API_KEY"]},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 3000},
        },
    )
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    st.error(f"Error en Gemini: {r.status_code} – {r.text}")
    raise RuntimeError("Fallo la llamada a Gemini.")

# --------------------------------------------------------------------------- #
#  Reemplazo de placeholders en Docs                                          #
# --------------------------------------------------------------------------- #

def replace_placeholder(doc_id: str, placeholder: str, new_text: str):
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "replaceAllText": {
                        "containsText": {"text": placeholder, "matchCase": True},
                        "replaceText": new_text,
                    }
                }
            ]
        },
    ).execute()

# --------------------------------------------------------------------------- #
#  1 · Generar los fragmentos del syllabus                                    #
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner=False)
def generar_componentes_taller(
    nombre_taller: str,
    nivel: str,
    industria: str,
    publico: str,
    objetivos_raw: str,
    horas: int,
):
    """Devuelve todas las piezas necesarias para llenar la plantilla."""

    prompt = f"""
## LEARNLM_ENABLE
## TASK: Generación de Syllabus para Taller
## REQUIRE_THOUGHT:
Plan → Borrador → Crítica interna → Respuesta final bajo ETIQUETAS

Eres una **diseñadora instruccional** experta en talleres intensivos de datos y negocio.
Aplica *Backward Design*, verbos de *Bloom* y la metodología **5E**.

Contexto
--------
• Taller: {nombre_taller}
• Nivel: {nivel}
• Industria: {industria}
• Público: {publico}
• Objetivos iniciales:
{objetivos_raw}
• Duración: {horas} h (≈1 sesión/hora; si <4 h fusiona fases apropiadamente)

=== Instrucciones específicas ===
1. **Generalidades del programa**: redáctalas en un párrafo nutrido (qué problema resuelve, beneficio para el participante y competencias que desarrollará y metodologia).
2. **Perfil de ingreso**: párrafo claro con habilidades y conocimientos previos requeridos (no sólo copiar el público objetivo).
3. **Detalles del plan**: lista con viñetas (una por sesión) → «• Sesión 1: Título – breve descripción (≤20 palabras)».

=== Formato de salida ===
[PERFIL_INGRESO]
...
[OBJETIVOS]
...
[PERFIL_EGRESO]
...
[DESCRIPCION_PLAN]
...
[DETALLES_PLAN]
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
"""

    raw = call_gemini(prompt)

    def ext(tag: str):
        m = re.search(rf"\[{tag}\]\n(.*?)(?=\n\[|\Z)", raw, re.S)
        return m.group(1).strip() if m else ""

    return {
        "perfil_ingreso": ext("PERFIL_INGRESO"),
        "objetivos": ext("OBJETIVOS"),
        "perfil_egreso": ext("PERFIL_EGRESO"),
        "descripcion_plan": ext("DESCRIPCION_PLAN"),
        "detalles_plan": ext("DETALLES_PLAN"),
        "outline": ext("OUTLINE"),
        "titulo1": ext("TITULO_PRIMER_OBJETIVO_SECUNDARIO"),
        "desc1": ext("DESCRIPCION_PRIMER_OBJETIVO_SECUNDARIO"),
        "titulo2": ext("TITULO_SEGUNDO_OBJETIVO_SECUNDARIO"),
        "desc2": ext("DESCRIPCION_SEGUNDO_OBJETIVO_SECUNDARIO"),
        "titulo3": ext("TITULO_TERCER_OBJETIVO_SECUNDARIO"),
        "desc3": ext("DESCRIPCION_TERCER_OBJETIVO_SECUNDARIO"),
    }

# --------------------------------------------------------------------------- #
#  2 · Crear el syllabus en Google Docs                                       #
# --------------------------------------------------------------------------- #

SYLLABUS_TEMPLATE_ID = "1I2jMQ1IjmG6_22dC7u6LYQfQzlND4WIvEusd756LFuo"

def crear_syllabus_en_docs(nombre_taller: str, horas: int, partes: dict, anio: int | None = None) -> str:
    """Copia la plantilla y sustituye los placeholders con los datos del taller."""

    if anio is None:
        anio = datetime.datetime.utcnow().year

    doc_id = (
        drive_service.files()
        .copy(fileId=SYLLABUS_TEMPLATE_ID, body={"name": f"Syllabus – {nombre_taller}"})
        .execute()["id"]
    )

    placeholders = [
        ("{{nombre_del_curso}}", nombre_taller),
        ("{{anio}}", str(anio)),
        ("{{generalidades_del_programa}}", partes["descripcion_plan"]),
        ("{{perfil_ingreso}}", partes["perfil_ingreso"]),
        ("{{perfil_egreso}}", partes["perfil_egreso"]),
        ("{{objetivos_generales}}", partes["objetivos"]),
        ("{{detalles_plan_estudios}}", partes["detalles_plan"]),
        ("{{outline}}", partes["outline"]),
        ("{{titulo_primer_objetivo_secundario}}", partes["titulo1"]),
        ("{{descripcion_primer_objetivo_secundario}}", partes["desc1"]),
        ("{{titulo_segundo_objetivo_secundario}}", partes["titulo2"]),
        ("{{descripcion_segundo_objetivo_secundario}}", partes["desc2"]),
        ("{{titulo_tercer_objetivo_secundario}}", partes["titulo3"]),
        ("{{descripcion_tercer_objetivo_secundario}}", partes["desc3"]),
    ]

    for ph, val in placeholders:
        replace_placeholder(doc_id, ph, val)
    # Permiso de escritura al dominio
    drive_service.permissions().create(
        fileId=doc_id,
        body={"type": "domain", "role": "writer", "domain": "datarebels.mx"},
        fields="id",
    ).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"
