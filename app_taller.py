import streamlit as st
from utils_taller import (
    generar_datos_generales,
    generar_syllabus_completo,
)


# Configuración de la página de Streamlit
st.set_page_config(page_title="Generador de Syllabus", layout="centered")
st.title("🧠 Generador de Syllabus y Outline")
st.markdown("Completa los campos del curso para generar automáticamente el syllabus y el outline.")

# === Inputs del curso ===
nombre = st.text_input("Nombre del taller")
nivel = st.selectbox("Nivel del taller", ["básico", "intermedio", "avanzado"])
publico = st.text_area("Público objetivo")
objetivos_raw = st.text_area("Objetivos del curso")
industria  = st.text_input("Industria")
horas = st.number_input("Horas totales", 1, 16, 4, 1)


# ✅ NUEVO BLOQUE: Mostrar links si ya se generaron previamente
if "link_syllabus" in st.session_state and "link_outline" in st.session_state:
    st.success("✅ Syllabu previamente generados.")
    col1 = st.columns(2)
    with col1:
        st.markdown(f"[📄 Ver Syllabus en Google Docs]({st.session_state['link_syllabus']})", unsafe_allow_html=True)
   

# Perfil fijo del estudiante tipo
student_persona = (
    "Usuario de negocios quiere construir productos de datos pero:\n"
    "- No tiene el hábito o modelo de trabajo mental de tomar decisiones basadas en datos.\n"
    "- No tiene conocimiento suficiente para traducir sus problemas a productos de datos.\n"
    "- No tiene habilidades técnicas para manipular data.\n"
    "- No colabora activamente con equipos de data.\n"
    "- Tiene poco tiempo y necesita soluciones prácticas que le ayuden a avanzar ya."
)

# === Acción principal: Generar syllabus y outline ===
if st.button("Generar Syllabus"):
    with st.spinner("Generando contenido con IA..."):
        try:
            perfil_ingreso, objetivos_mejorados, perfil_egreso, outline, \
            titulo1, desc1, titulo2, desc2, titulo3, desc3 = generar_datos_generales(
                nombre, nivel, publico, student_persona, industria, objetivos_raw, horas
            )

            link_syllabus = generar_syllabus_completo(
                nombre, nivel, objetivos_mejorados, publico, industria,
                perfil_ingreso, perfil_egreso, outline,
                titulo1, desc1, titulo2, desc2, titulo3, desc3
            )

       
            # ✅ Guardar los links para mantenerlos visibles
            st.session_state["link_syllabus"] = link_syllabus
         

            st.success("✅ Syllabus y Outline generados correctamente.")
            col1 = st.columns(2)
            with col1:
                st.markdown(f"[📄 Ver Syllabus en Google Docs]({link_syllabus})", unsafe_allow_html=True)
      
        except Exception as e:
            st.error(f"Ha ocurrido un error durante la generación: {str(e)}")
            st.info("Verifica que todos los campos estén completos y que la plantilla tenga los placeholders correctos.")
            st.info("Placeholders necesarios en la plantilla: {{titulo_primer_objetivo_secundario}}, {{descripcion_primer_objetivo_secundario}}, etc.")
