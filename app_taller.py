import streamlit as st
from utils_taller import (
    generar_componentes_taller,
    crear_syllabus_en_docs,
)

st.set_page_config(page_title="Generador de Syllabus para Talleres", layout="centered")
st.title("🛠️ Generador de Syllabus")

st.markdown(
    """
Completa los campos del **taller** y obtén un documento de syllabus en Google Docs.
"""
)

# ── Inputs ──────────────────────────────────────────────────────────────────────
nombre         = st.text_input("Nombre del taller")
nivel          = st.selectbox("Nivel del taller", ["básico", "intermedio", "avanzado"])
industria      = st.text_input("Industria objetivo (ej. retail, manufactura, banca)")
publico        = st.text_area("Público objetivo")
objetivos_raw  = st.text_area("Objetivos del taller")
horas          = st.number_input("Horas totales del taller", 1, 24, 4, 1)

# ── Mostrar link si ya existe ──────────────────────────────────────────────────
if "taller_link_syllabus" in st.session_state:
    st.success("✅ Syllabus previamente generado:")
    st.markdown(f"[📄 Ver Syllabus]({st.session_state['taller_link_syllabus']})", unsafe_allow_html=True)

# ── Acción principal ───────────────────────────────────────────────────────────
if st.button("Generar syllabus"):
    if not all([nombre, industria, publico, objetivos_raw]):
        st.warning("Completa todos los campos antes de continuar.")
        st.stop()

    with st.spinner("Generando con IA…"):
        try:
            # 1. Obtiene componentes (incluye outline markdown para incrustarlo en el Doc)
            (perfil_ingreso,
             objetivos_finales,
             perfil_egreso,
             outline_md,
             obj1_t, obj1_d,
             obj2_t, obj2_d,
             obj3_t, obj3_d) = generar_componentes_taller(
                nombre, nivel, industria, publico, objetivos_raw, horas
            )

            # 2. Crea únicamente el syllabus (ya no genera hoja de cálculo)
            link_syllabus = crear_syllabus_en_docs(
                nombre, nivel, industria, horas,
                perfil_ingreso, perfil_egreso, objetivos_finales, outline_md,
                obj1_t, obj1_d, obj2_t, obj2_d, obj3_t, obj3_d
            )

            # 3. Guarda y muestra el enlace
            st.session_state["taller_link_syllabus"] = link_syllabus
            st.success("✅ ¡Syllabus generado correctamente!")
            st.markdown(f"[📄 Ver Syllabus]({link_syllabus})", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
