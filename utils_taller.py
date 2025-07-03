"""
Utilidades para generar un syllabus de taller:
1. llamar a Gemini,
2. crear bloques base (perfil, objetivos, outline…),
3. refinar secciones clave (generalidades, perfil_ingreso, detalles),
4. rellenar la plantilla de Google Docs.
"""

from __future__ import annotations
import json, re, tempfile, requests, streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ───────────────────────── Google creds ──────────────────────────
with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
    json.dump(json.loads(st.secrets["SERVICE_ACCOUNT_JSON"]), f)
    SERVICE_ACCOUNT_FILE = f.name

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
docs_service = build("docs", "v1", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)

# ID de la plantilla con placeholders del syllabus
TEMPLATE_ID = "1I2jMQ1IjmG6_22dC7u6LYQfQzlND4WIvEusd756LFuo"

# ───────────────────────── Gemini helper ─────────────────────────
def call_gemini(prompt: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-1.5-flash-latest:generateContent"
    )
    r = requests.post(
        url,
        params={"key": st.secrets["GEMINI_API_KEY"]},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 3000},
        },
        timeout=90,
    )
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raise RuntimeError(f"Gemini error {r.status_code}: {r.text}")


# ───────────────────────── Bloques base ──────────────────────────
@st.cache_data(show_spinner=False)
def generar_bloques(
    nombre: str,
    nivel: str,
    industria: str,
    publico: str,
    objetivos_raw: str,
    horas: int,
) -> dict[str, str]:
    """
    Pide a Gemini los bloques delimitados por etiquetas —manteniendo nomenclatura
    de placeholders— y devuelve un diccionario con cada sección.
    """
    prompt = f"""
Eres diseñador instruccional senior en talleres de IA, Ciencia de Datos y Negocios.
Genera los bloques para un syllabus conservando exactamente los placeholders.

Taller.............: {nombre}
Nivel..............: {nivel}
Industria..........: {industria}
Público objetivo...: {publico}
Objetivos iniciales: {objetivos_raw}
Duración total.....: {horas} h

Instrucciones clave
-------------------
• Ajusta ejemplos/casos a la INDUSTRIA.  
• Si horas > 4, divide agenda en **Día 1 / Día 2** (mitad de horas por día).  
• Usa best-practices hands-on de IA orientados a negocio.  

Devuelve únicamente el contenido separado con estas etiquetas:

[PERFIL_INGRESO]
...
[OBJETIVOS]
...
[PERFIL_EGRESO]
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
    texto = call_gemini(prompt)

    def _extr(tag):
        m = re.search(rf"\[{tag}]\n(.*?)(?=\[|$)", texto, re.S)
        return m.group(1).strip() if m else ""

    return {
        "perfil_ingreso": _extr("PERFIL_INGRESO"),
        "objetivos": _extr("OBJETIVOS"),
        "perfil_egreso": _extr("PERFIL_EGRESO"),
        "outline": _extr("OUTLINE"),
        "t1": _extr("TITULO_PRIMER_OBJETIVO_SECUNDARIO"),
        "d1": _extr("DESCRIPCION_PRIMER_OBJETIVO_SECUNDARIO"),
        "t2": _extr("TITULO_SEGUNDO_OBJETIVO_SECUNDARIO"),
        "d2": _extr("DESCRIPCION_SEGUNDO_OBJETIVO_SECUNDARIO"),
        "t3": _extr("TITULO_TERCER_OBJETIVO_SECUNDARIO"),
        "d3": _extr("DESCRIPCION_TERCER_OBJETIVO_SECUNDARIO"),
    }


# ────────────── Refinar y construir el syllabus completo ─────────
def generar_syllabus_completo(
    nombre: str,
    nivel: str,
    objetivos_mejorados: str,
    publico: str,
    siguiente: str,
    perfil_ingreso: str,
    perfil_egreso: str,
    outline: str,
    t1: str,
    d1: str,
    t2: str,
    d2: str,
    t3: str,
    d3: str,
) -> str:
    """
    1. Pide a Gemini las secciones refinadas (generalidades, perfil_ingreso, detalles),
    2. copia la plantilla de Google Docs,
    3. reemplaza todos los placeholders y devuelve la URL editable.
    """
    anio = 2025

    def pedir_seccion(etiqueta: str, instruccion: str) -> str:
        prompt = f"""
Como experto en diseño instruccional y aplicando principios de LearnLM,
genera SOLO la sección [{etiqueta}] para el syllabus.

Curso: {nombre}
Nivel: {nivel}
Año: {anio}
Objetivos mejorados: {objetivos_mejorados}

Perfil de ingreso: {perfil_ingreso}
Perfil de egreso: {perfil_egreso}

Outline:
{outline}

{instruccion}
"""
        return call_gemini(prompt).strip()

    generalidades = pedir_seccion(
        "GENERALIDADES_DEL_PROGRAMA",
        "Redacta un párrafo que combine descripción, propósito y conexión con la industria.",
    )
    ingreso_refinado = pedir_seccion(
        "PERFIL_INGRESO",
        "Redacta un párrafo claro y directo del perfil de ingreso.",
    )
    detalles = pedir_seccion(
        "DETALLES_PLAN_ESTUDIOS",
        "Convierte el outline en bullets por sesión (sin negritas).",
    )

    # ─── Copiar plantilla y reemplazar ───
    doc_id = (
        drive_service.files()
        .copy(fileId=TEMPLATE_ID, body={"name": f"Syllabus - {nombre}"})
        .execute()["id"]
    )

    mapping = {
        "{{nombre_del_curso}}": nombre,
        "{{anio}}": str(anio),
        "{{generalidades_del_programa}}": generalidades,
        "{{perfil_ingreso}}": ingreso_refinado,
        "{{perfil_egreso}}": perfil_egreso,
        "{{detalles_plan_estudios}}": detalles,
        "{{titulo_primer_objetivo_secundario}}": t1,
        "{{descripcion_primer_objetivo_secundario}}": d1,
        "{{titulo_segundo_objetivo_secundario}}": t2,
        "{{descripcion_segundo_objetivo_secundario}}": d2,
        "{{titulo_tercer_objetivo_secundario}}": t3,
        "{{descripcion_tercer_objetivo_secundario}}": d3,
    }

    for ph, val in mapping.items():
        _replace(doc_id, ph, val)

    # Permiso de edición al dominio
    drive_service.permissions().create(
        fileId=doc_id,
        body={"type": "domain", "role": "writer", "domain": "datarebels.mx"},
        fields="id",
    ).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"


# helper interno
def _replace(doc_id: str, placeholder: str, new_text: str) -> None:
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
