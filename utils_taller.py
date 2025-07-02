import os
import io
import re
import tempfile
import pandas as pd
import requests
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --------------------------------------------------------------------------- #
#  Credenciales y servicios de Google                                         #
# --------------------------------------------------------------------------- #
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
    f.write(st.secrets["SERVICE_ACCOUNT_JSON"])
    SERVICE_JSON = f.name

creds = service_account.Credentials.from_service_account_file(
    SERVICE_JSON, scopes=SCOPES
)
docs = build("docs", "v1", credentials=creds)
drive = build("drive", "v3", credentials=creds)
sheets = build("sheets", "v4", credentials=creds)

# --------------------------------------------------------------------------- #
#  Llamada a Gemini‑1.5‑Flash                                                 #
# --------------------------------------------------------------------------- #

def call_gemini(prompt: str) -> str:
    """Llama al endpoint REST de Gemini 1.5 Flash y devuelve solo el texto."""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
    )
    headers = {"Content-Type": "application/json"}
    params = {"key": st.secrets["GEMINI_API_KEY"]}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 3000},
    }

    r = requests.post(url, headers=headers, params=params, json=data)
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    st.error(f"Error en API Gemini: {r.status_code} – {r.text}")
    raise RuntimeError("Fallo la llamada a Gemini.")

# --------------------------------------------------------------------------- #
#  Utilidad de reemplazo en Google Docs                                       #
# --------------------------------------------------------------------------- #

def docs_replace(doc_id: str, placeholder: str, new_text: str):
    docs.documents().batchUpdate(
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
#  1. Generar componentes del taller con IA                                   #
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner=False)
def generar_componentes_taller(
    nombre: str,
    nivel: str,
    industria: str,
    publico: str,
    obj_raw: str,
    horas: int,
):
    """Devuelve perfil de ingreso, objetivos, perfil de egreso y outline."""

    prompt = f"""
## LEARNLM_ENABLE
## TASK: Generación de Syllabus para Taller
## REQUIRE_THOUGHT:
Planear → Borrador → Autocrítica → Respuesta final bajo ETIQUETAS

Eres una **diseñadora instruccional galardonada** especializada en talleres de datos, inteligencia artificial ynegocio.
Crea un **syllabus de taller** aplicando las mejores prácticas de la industria:
• *Backward Design*, *Bloom* & *SOLO Taxonomy*.
• Bloques activos < 20 min.
• Resultados de aprendizaje **SMART** medibles.
• Metodología **5E** (Engage, Explore, Explain, Elaborate, Evaluate).

Contexto
--------
• Nombre del taller: {nombre}
• Nivel: {nivel}
• Industria objetivo: {industria}
• Público objetivo: {publico}
• Objetivos iniciales (uno por línea):
{obj_raw}
• Duración total: {horas} h (≈1 fila por hora; fusiona lógicamente si <4 h)

Instrucciones
-------------
1. Refina los objetivos en 3‑5 **resultados de aprendizaje finales** (verbos Bloom, SMART).
2. Escribe el **Perfil de Ingreso** (conocimientos previos) y el **Perfil de Egreso** (competencias logradas).
3. Diseña una tabla **outline** con exactamente {horas} filas y las columnas:
   | Sesión | Fase 5E | Título | Conceptos clave | Objetivo 1 | Objetivo 2 | Actividad dinámica | Descripción breve |
   – Incluye ejemplos/casos específicos de la industria {industria}.
4. Sigue los principios de *LearnLM*: tu razonamiento interno es privado; la salida para el usuario inicia bajo ETIQUETAS.

Formato de salida (sin texto extra)
-----------------------------------
[PERFIL_INGRESO]
<texto>
[OBJETIVOS]
<texto>
[PERFIL_EGRESO]
<texto>
[OUTLINE]
<tabla Markdown>
[T1]<título primer objetivo secundario>
[D1]<descripción primer objetivo>
[T2]...
[D2]...
[T3]...
[D3]...
"""

    raw = call_gemini(prompt)

    def _sec(tag: str):
        m = re.search(rf"\[{tag}\]\n(.*?)(?=\n\[|\Z)", raw, re.S)
        return m.group(1).strip() if m else ""

    return (
        _sec("PERFIL_INGRESO"),
        _sec("OBJETIVOS"),
        _sec("PERFIL_EGRESO"),
        _sec("OUTLINE"),
        _sec("T1"), _sec("D1"),
        _sec("T2"), _sec("D2"),
        _sec("T3"), _sec("D3"),
    )

# --------------------------------------------------------------------------- #
#  2. Crear Syllabus en Google Docs                                           #
# --------------------------------------------------------------------------- #

SYLLABUS_TEMPLATE_ID = "1I2jMQ1IjmG6_22dC7u6LYQfQzlND4WIvEusd756LFuo"

def crear_syllabus_en_docs(
    nombre: str,
    nivel: str,
    industria: str,
    horas: int,
    perfil_ingreso: str,
    perfil_egreso: str,
    objetivos: str,
    outline_md: str,
    t1: str,
    d1: str,
    t2: str,
    d2: str,
    t3: str,
    d3: str,
) -> str:

    new_doc = drive.files().copy(
        fileId=SYLLABUS_TEMPLATE_ID,
        body={"name": f"Syllabus – {nombre}"},
    ).execute()
    doc_id = new_doc["id"]

    mapping = {
        "{{nombre_del_curso}}": nombre,
        "{{generalidades_del_programa}}": f"Taller intensivo de {horas}h para el sector {industria}.",
        "{{perfil_ingreso}}": perfil_ingreso,
        "{{detalles_plan_estudios}}": outline_md,
        "{{titulo_primer_objetivo_secundario}}": t1,
        "{{descripcion_primer_objetivo_secundario}}": d1,
        "{{titulo_segundo_objetivo_secundario}}": t2,
        "{{descripcion_segundo_objetivo_secundario}}": d2,
        "{{titulo_tercer_objetivo_secundario}}": t3,
        "{{descripcion_tercer_objetivo_secundario}}": d3,
    }

    for ph, txt in mapping.items():
        docs_replace(doc_id, ph, txt)

    return f"https://docs.google.com/document/d/{doc_id}/edit"
