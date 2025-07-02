import streamlit as st
from utils_taller import (
    generar_componentes_taller,
    crear_syllabus_en_docs,
    crear_outline_en_sheets,
)

st.set_page_config(page_title="Generador de Taller", layout="centered")
st.title("🛠️ Generador de Syllabus & Outline para Talleres")

st.markdown(
    """
Introduce los datos del taller y obtén automáticamente:
* **Syllabus** (Google Docs)  
* **Outline** (Google Sheets)
"""
)

# ── Inputs ──────────────────────────────────────────────────────────────────────
nombre         = st.text_input("Nombre del taller")
nivel          = st.selectbox("Nivel del taller", ["básico", "intermedio", "avanzado"])
industria      = st.text_input("Industria objetivo (ej. retail, manufactura, banca)")
publico        = st.text_area("Público objetivo")
objetivos_raw  = st.text_area("Objetivos del taller — uno por línea")
horas          = st.number_input("Horas totales del taller", 1, 24, 4, 1)

# ── Acción ─────────────────────────────────────────────────────────────────────
if st.button("Generar syllabus y outline"):
    if not all([nombre, industria, publico, objetivos_raw]):
        st.warning("Completa todos los campos.")
        st.stop()

    with st.spinner("Generando con IA…"):
        try:
            (perfil_ingreso,
             objetivos_finales,
             perfil_egreso,
             outline_md,
             obj1_t, obj1_d,
             obj2_t, obj2_d,
             obj3_t, obj3_d) = generar_componentes_taller(
                nombre, nivel, industria, publico, objetivos_raw, horas
            )

            link_syllabus = crear_syllabus_en_docs(
                nombre, nivel, industria, horas, perfil_ingreso, perfil_egreso,
                objetivos_finales, outline_md,
                obj1_t, obj1_d, obj2_t, obj2_d, obj3_t, obj3_d,
            )
            link_outline = crear_outline_en_sheets(nombre, outline_md)

            st.success("¡Todo listo!")
            st.markdown(f"📄 **Syllabus:** [{link_syllabus}]({link_syllabus})")
            st.markdown(f"📊 **Outline:** [{link_outline}]({link_outline})")

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
