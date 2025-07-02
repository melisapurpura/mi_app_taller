import os, io, re, tempfile, pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.generativeai as genai

# --------------------------------------------------------------------------- #
#  Credenciales y servicios de Google                                         #
# --------------------------------------------------------------------------- #
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Carga del JSON de la service-account desde secrets
with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
    f.write(st.secrets["SERVICE_ACCOUNT_JSON"])
    SERVICE_JSON = f.name

creds   = service_account.Credentials.from_service_account_file(SERVICE_JSON, scopes=SCOPES)
docs    = build("docs",  "v1", credentials=creds)
drive   = build("drive", "v3", credentials=creds)
sheets  = build("sheets","v4", credentials=creds)

# --------------------------------------------------------------------------- #
#  Gemini-Pro call helper                                                     #
# --------------------------------------------------------------------------- #
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def call_gemini(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text.strip()

# --------------------------------------------------------------------------- #
#  Utilidades de Google Docs                                                  #
# --------------------------------------------------------------------------- #
def docs_replace(doc_id: str, placeholder: str, new_text: str):
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{
            "replaceAllText": {
                "containsText": {"text": placeholder, "matchCase": True},
                "replaceText": new_text,
            }
        }]}
    ).execute()

# --------------------------------------------------------------------------- #
#  1. Generar texto base con IA                                               #
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def generar_componentes_taller(nombre, nivel, industria, publico, obj_raw, horas):
    prompt = f"""
Actúa como diseñador instruccional experto en talleres de negocios y datos.
Con la siguiente información genera las secciones solicitadas, SIN explicaciones extra.

Taller: {nombre}
Nivel: {nivel}
Industria: {industria}
Público objetivo: {publico}
Objetivos iniciales:
{obj_raw}

Duración total: {horas} horas
Requisitos:
- Ajusta ejemplos al sector {industria}.
- El outline tendrá exactamente {horas} filas (una por hora).
- Formato Markdown | Sesión | Título | Conceptos clave | Objetivo 1 | Objetivo 2 | Descripción |

Devuelve en este orden:

[PERFIL_INGRESO]
…
[OBJETIVOS]
…
[PERFIL_EGRESO]
…
[OUTLINE]
…
[T1]…[D1]…[T2]…[D2]…[T3]…[D3]
"""
    texto = call_gemini(prompt)

    def extra(etq):  # tiny extractor
        m = re.search(rf"\[{etq}\]\n(.*?)(?=\[|\Z)", texto, re.S)
        return m.group(1).strip() if m else ""

    return (
        extra("PERFIL_INGRESO"),
        extra("OBJETIVOS"),
        extra("PERFIL_EGRESO"),
        extra("OUTLINE"),
        extra("T1"), extra("D1"),
        extra("T2"), extra("D2"),
        extra("T3"), extra("D3"),
    )

# --------------------------------------------------------------------------- #
#  2. Crear Syllabus en Google Docs                                           #
# --------------------------------------------------------------------------- #
SYLLABUS_TEMPLATE_ID = "1I2jMQ1IjmG6_22dC7u6LYQfQzlND4WIvEusd756LFuo"  # tu plantilla

def crear_syllabus_en_docs(nombre, nivel, industria, horas,
                           perfil_ingreso, perfil_egreso, objetivos, outline_md,
                           t1, d1, t2, d2, t3, d3):

    # Copiar template
    new_doc = drive.files().copy(
        fileId=SYLLABUS_TEMPLATE_ID,
        body={"name": f"Syllabus – {nombre}"}
    ).execute()
    doc_id = new_doc["id"]

    # Reemplazos
    mapping = {
        "{{nombre_del_curso}}": nombre,
        "{{generalidades_del_programa}}": f"Este taller de {horas} h cubre {industria}.",
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

# --------------------------------------------------------------------------- #
#  3. Crear Outline en Google Sheets                                          #
# --------------------------------------------------------------------------- #
def crear_outline_en_sheets(nombre: str, outline_md: str) -> str:
    filas = [l for l in outline_md.splitlines() if "|" in l and not l.startswith("|---")]
    df = pd.read_csv(io.StringIO("\n".join(filas)), sep="|", engine="python").dropna(axis=1, how="all")
    df.columns = [c.strip() for c in df.columns]

    sheet = sheets.spreadsheets().create(
        body={"properties": {"title": f"Outline – {nombre}"}},
        fields="spreadsheetId"
    ).execute()
    sid = sheet["spreadsheetId"]

    sheets.spreadsheets().values().update(
        spreadsheetId=sid, range="A1",
        valueInputOption="RAW",
        body={"values": [df.columns.tolist()] + df.values.tolist()}
    ).execute()

    return f"https://docs.google.com/spreadsheets/d/{sid}/edit"
