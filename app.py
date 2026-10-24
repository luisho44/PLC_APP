import streamlit as st
import time
from datetime import date
from base_datos import conectar_supabase, agente_guardar_historial, agente_obtener_historial
from logica_plc import Rung, Contacto, Bobina
from interfaz import dibujar_ladder

st.set_page_config(page_title="PLC Academy IA", layout="wide")

# --- ESTADO INICIAL ---
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.rungs = []
    st.session_state.entradas = {"Start": False, "Stop": False}
    st.session_state.start_time = time.time()

supabase = conectar_supabase()

# --- LOGIN ---
if st.session_state.user is None:
    st.title("⚙️ PLC Academy con Agente IA")
    with st.form("login"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                st.session_state.start_time = time.time()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    st.stop()

# --- CALCULO DE TIEMPO ---
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()
minutos_estudiados = int((time.time() - st.session_state.start_time) // 60)

# --- INTERFAZ PRINCIPAL ---
col1, col2 = st.columns([8, 2])
with col1:
    st.write(f"**Alumno:** {st.session_state.user.email}")
with col2:
    if st.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

st.divider()

tabs = st.tabs(["🤖 Agente IA (Progreso)", "💻 Simulador PLC", "📚 Clases Diarias"])

# --- PESTAÑA 1: EL AGENTE ---
with tabs[0]:
    st.subheader("Panel del Agente de Aprendizaje")
    historial = agente_obtener_historial(supabase, st.session_state.user.id)
    
    # Cálculos del agente
    total_misiones = len(historial)
    tiempo_total = sum(item['minutos_estudiados'] for item in historial) + minutos_estudiados
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Misiones Completadas", total_misiones)
    c2.metric("Tiempo Total de Estudio", f"{tiempo_total} min")
    c3.metric("Tiempo en esta sesión", f"{minutos_estudiados} / 60 min")

    if minutos_estudiados >= 60:
        st.warning("⚠️ El Agente recomienda descansar. Has alcanzado el límite diario de 60 minutos para evitar fatiga mental.")
        if st.button("Guardar Progreso de Hoy y Reiniciar"):
            agente_guardar_historial(supabase, st.session_state.user.id, minutos_estudiados, "Sesión Diaria")
            st.session_state.start_time = time.time()
            st.success("Progreso guardado. ¡Buen trabajo hoy!")
            st.rerun()

    st.divider()
    st.write("**Historial de Avance (Agente):**")
    if not historial:
        st.info("El agente aún no tiene registros. Completa misiones para guardar tu avance.")
    else:
        for h in reversed(historial[-5:]): # Muestra los últimos 5
            st.write(f"- Misión: {h['mision_completada']} | Tiempo: {h['minutos_estudiados']} min")

# --- PESTAÑA 2: SIMULADOR ---
with tabs[1]:
    st.subheader("Entorno de Simulación")
    
    cols = st.columns(len(st.session_state.entradas))
    for i, nombre in enumerate(list(st.session_state.entradas.keys())):
        with cols[i]:
            st.session_state.entradas[nombre] = st.toggle(nombre, value=st.session_state.entradas[nombre])

    if not st.session_state.rungs:
        st.info("Carga una clase desde la pestaña 'Clases Diarias'.")
    else:
        dibujar_ladder(st.session_state.rungs, st.session_state.entradas)

# --- PESTAÑA 3: CLASES (El Agente las actualiza) ---
with tabs[2]:
    st.subheader("Clases Diarias")
    
    st.markdown("""
    ### Módulo 1: Fundamentos
    *Un PLC es una computadora industrial. Nació en 1968 para reemplazar los relés. Las marcas más famosas son Siemens (TIA Portal), Allen-Bradley (Studio 5000) y ABB.*
    """)
    
    if st.button("Cargar Práctica 1: Enclavamiento", type="primary"):
        st.session_state.rungs = [
            Rung([Contacto("Start", "NA")], Bobina("Lamp")),
            Rung([Contacto("Lamp", "NA"), Contacto("Stop", "NC")], Bobina("Lamp"))
        ]
        st.session_state.entradas = {"Start": False, "Stop": False}
        st.success("Práctica cargada en el Simulador.")
        st.rerun()
        
    st.divider()
    if st.button("Guardar Misión Completada en el Agente IA"):
        agente_guardar_historial(supabase, st.session_state.user.id, minutos_estudiados, "Enclavamiento")
        st.success("¡El Agente ha guardado tu avance en la nube!")
