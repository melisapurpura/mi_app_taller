import streamlit as st
from utils_taller import generar_bloques, generar_syllabus_completo

st.set_page_config(page_title="Generador de Syllabus de Taller", page_icon="🛠️")
st.title("🛠️ Generador de Syllabus de Taller")

# ───────────── Inputs ─────────────
nombre     = st.text_input("Nombre del taller")
nivel      = st.selectbox("Nivel", ["básico", "intermedio", "avanzado"])
industria  = st.text_input("Industria")
publico    = st.text_area("Público objetivo")
objetivos  = st.text_area("Objetivos (uno por línea)")
horas      = st.number_input("Horas totales", 1, 16, 4, 1)

if st.button("Generar Syllabus"):
    if "" in [nombre, industria, publico, objetivos]:
        st.warning("⚠️ Completa todos los campos.")
        st.stop()

    with st.spinner("Generando con IA…"):
        try:
            bloques = generar_bloques(
                nombre, nivel, industria, publico, objetivos, int(horas)
            )
            link = generar_syllabus_completo(
                nombre,
                nivel,
                bloques["objetivos"],
                publico,
                "",                      # «siguiente» no aplica al taller
                bloques["perfil_ingreso"],
                bloques["perfil_egreso"],
                bloques["outline"],
                bloques["t1"],
                bloques["d1"],
                bloques["t2"],
                bloques["d2"],
                bloques["t3"],
                bloques["d3"],
            )
            st.success("✅ Syllabus listo.")
            st.markdown(f"[📄 Abrir Syllabus]({link})", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.info("Verifica credenciales y APIs.")
