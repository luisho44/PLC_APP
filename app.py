import streamlit as st
import pandas as pd
import time
import google.generativeai as genai
from datetime import datetime, timezone
from base_datos import (
    conectar_supabase, agente_guardar_historial, obtener_misiones_completadas, 
    admin_ver_todos_los_usuarios, admin_ver_todo_el_progreso,
    obtener_tiempo_inicio, guardar_tiempo_inicio
)
from logica_plc import Rung, Contacto, Bobina, Temporizador, Contador, Comparador
from interfaz import dibujar_ladder, dibujar_gemelo_digital
from misiones import obtener_temario

# =====================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =====================================================================
st.set_page_config(page_title="PLC Academy Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0e1117; }
    .profile-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 20px;}
    .timer-box { background-color: #262730; padding: 10px; border-radius: 8px; text-align: center; font-size: 16px; font-weight: bold; border: 1px solid #555;}
    .eval-box { background-color: #1e1e1e; padding: 15px; border-radius: 8px; border-left: 5px solid #ffaa00; margin-top: 15px;}
    .symbol-card { background-color: #1e1e1e; padding: 20px; border-radius: 8px; border: 1px solid #333; text-align: center; margin-bottom: 15px;}
    .symbol-icon { font-size: 24px; font-family: monospace; font-weight: bold; color: #00ff00; display: block; margin: 10px 0;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. CONEXIONES Y ESTADO
# =====================================================================
supabase = conectar_supabase()
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_KEY: genai.configure(api_key=GEMINI_KEY)

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = "student"
    st.session_state.username = None
    st.session_state.rungs = []
    st.session_state.entradas = {"Start": False, "Stop": False}
    st.session_state.variables_num = {"Temperatura": 0} # NUEVO: Para comparadores
    st.session_state.teoria_actual = ""
    st.session_state.evaluacion_actual = ""
    st.session_state.nivel_actual = 1
    st.session_state.explicacion_simbolo = ""
    st.session_state.start_time = None

# =====================================================================
# 3. FUNCIONES DE IA
# =====================================================================
def generar_teoria_ia(tema, prompt):
    if not GEMINI_KEY: return "Falta la API Key."
    try:
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        response = model.generate_content(f"Eres un instructor de PLC. Tema: '{tema}'. {prompt} Responde en 2 párrafos.")
        return response.text
    except Exception as e: return f"Error de IA: {e}"

def evaluar_codigo_ia(codigo_actual, nivel_actual):
    if not GEMINI_KEY: return "Falta la API Key."
    try:
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        prompt = f"Eres profesor de PLC. Alumno en Nivel {nivel_actual}. Código: {codigo_actual}. Revisa errores lógicos (flancos, enclavamientos, comparadores). Corrige constructivamente."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Error: {e}"

def explicar_simbolo_ia(simbolo):
    if not GEMINI_KEY: return "Falta la API Key."
    try:
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        response = model.generate_content(f"Explica brevemente para qué sirve el símbolo Ladder '{simbolo}' en PLCs.")
        return response.text
    except Exception as e: return f"Error: {e}"

# =====================================================================
# 4. LOGIN Y CABECERA (Resumido para ahorrar espacio, igual que antes)
# =====================================================================
if st.session_state.user is None:
    st.title("⚙️ PLC Academy Pro")
    with st.form("login"):
        email = st.text_input("Email"); pw = st.text_input("Password", type="password")
        if st.form_submit_button("Iniciar Sesión", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                rol = supabase.table("user_roles").select("role").eq("user_id", res.user.id).execute()
                st.session_state.role = rol.data[0]["role"] if rol.data else "student"
                perfil = supabase.table("profiles").select("username").eq("id", res.user.id).execute()
                st.session_state.username = perfil.data[0].get("username") if perfil.data else None
                t_inicio = obtener_tiempo_inicio(st.session_state.user.id)
                st.session_state.start_time = t_inicio if t_inicio else datetime.now(timezone.utc)
                if not t_inicio: guardar_tiempo_inicio(st.session_state.user.id)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    st.stop()

if st.session_state.username is None:
    with st.form("nombre_form"):
        nuevo_nombre = st.text_input("Tu nombre o apodo:")
        if st.form_submit_button("Guardar Nombre"):
            if nuevo_nombre:
                supabase.table("profiles").update({"username": nuevo_nombre}).eq("id", st.session_state.user.id).execute()
                st.session_state.username = nuevo_nombre; st.rerun()
    st.stop()

# Cálculo reloj
if st.session_state.start_time is None: st.session_state.start_time = datetime.now(timezone.utc)
try:
    dif = datetime.now(timezone.utc) - st.session_state.start_time
    minutos_restantes = max(0, 60 - int(dif.total_seconds() // 60))
except: minutos_restantes = 60

col_p, col_t, col_l = st.columns([6, 2, 2])
with col_p:
    color = "#ff4b4b" if st.session_state.role == "admin" else "#007bff"
    st.markdown(f"<div class='profile-header'><h2 style='margin: 0;'>👤 {st.session_state.username}</h2><span style='background-color: {color}; padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white;'>ROL: {'ADMINISTRADOR' if st.session_state.role == 'admin' else 'ESTUDIANTE'}</span></div>", unsafe_allow_html=True)
with col_t: st.markdown(f"<div class='timer-box'>⏱️ Tiempo restante:<br><span style='font-size:24px; color:#00ff00;'>{minutos_restantes} min</span></div>", unsafe_allow_html=True)
with col_l:
    if st.button("Cerrar Sesión", use_container_width=True):
        supabase.auth.sign_out(); st.session_state.clear(); st.rerun()

if minutos_restantes <= 0:
    st.error("🛑 ¡Tiempo de estudio completado por hoy!")
    if st.button("Reiniciar reloj"): 
        st.session_state.start_time = datetime.now(timezone.utc); guardar_tiempo_inicio(st.session_state.user.id); st.rerun()
    st.stop()

# =====================================================================
# 5. PESTAÑAS
# =====================================================================
tabs_list = ["💻 Simulador Ladder", "🗺️ Ruta de Aprendizaje", "📖 Biblioteca de Símbolos", "⚙️ Mi Perfil"]
if st.session_state.role == "admin": tabs_list.append("🛡️ Panel Admin")
tabs = st.tabs(tabs_list, key="main_tabs", on_change="rerun")

# =====================================================================
# 6. SIMULADOR
# =====================================================================
with tabs[0]:
    if st.session_state.teoria_actual:
        st.info(f"📖 **Teoría:**\n\n{st.session_state.teoria_actual}")
            
    col_io, col_ladder = st.columns([1, 3])
    with col_io:
        st.markdown("### Panel I/O")
        for nombre in list(st.session_state.entradas.keys()):
            if nombre in ["Start", "Stop"]:
                st.session_state.entradas[nombre] = st.button(f"Pulsar {nombre}", key=f"btn_{nombre}", use_container_width=True)
            else:
                st.session_state.entradas[nombre] = st.toggle(nombre, value=st.session_state.entradas[nombre])
        
        st.divider()
        st.markdown("### Variables Numéricas")
        st.session_state.variables_num["Temperatura"] = st.number_input("Sensor Temperatura", value=st.session_state.variables_num.get("Temperatura", 0))
            
    with col_ladder:
        st.markdown("### Código Ladder")
        if not st.session_state.rungs: st.info("Usa el Constructor de abajo.")
        else:
            dibujar_ladder(st.session_state.rungs, st.session_state.entradas, st.session_state.variables_num)
            st.divider()
            dibujar_gemelo_digital(st.session_state.rungs)
            
            if st.button("🤖 Pedir al Tutor IA que evalúe mi código", type="secondary", use_container_width=True):
                codigo_resumen = []
                for i, r in enumerate(st.session_state.rungs):
                    c_desc = [f"{c.nombre}({c.tipo})" for c in r.contactos]
                    codigo_resumen.append(f"Rung {i+1}: [{ ' + '.join(c_desc) }] --- ( {r.elemento.nombre} )")
                with st.spinner("El Tutor IA está revisando..."):
                    st.session_state.evaluacion_actual = evaluar_codigo_ia(" | ".join(codigo_resumen), st.session_state.nivel_actual)
            
            if st.session_state.evaluacion_actual:
                st.markdown(f"<div class='eval-box'>🎓 <b>Evaluación:</b><br><br>{st.session_state.evaluacion_actual}</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🛠️ Constructor de Ladder")
    with st.form("ladder_builder"):
        c1, c2 = st.columns(2)
        c_nombre = c1.text_input("Contacto", value="Start")
        c_tipo = c2.selectbox("Tipo Contacto", ["NA", "NC", "P (Flanco Subida)", "N (Flanco Bajada)"])
        
        st.markdown("**Elemento de Salida:**")
        c3, c4 = st.columns(2)
        tipo_elem = c3.selectbox("Elemento", ["Bobina Normal", "Bobina Set", "Bobina Reset", "Temporizador TON", "Temporizador TOF", "Contador CTU", "Contador CTD", "Comparador"])
        n_elem = c4.text_input("Nombre Elemento", value="Lamp" if "Bobina" in tipo_elem else ("Motor" if "Temporizador" in tipo_elem or "Contador" in tipo_elem else "Temperatura"))
        
        if st.form_submit_button("Añadir Rung", type="primary"):
            t_c = "P" if "P (" in c_tipo else ("N" if "N (" in c_tipo else c_tipo)
            c = Contacto(c_nombre, t_c)
            
            if tipo_elem == "Bobina Normal": elem = Bobina(n_elem, "Normal")
            elif tipo_elem == "Bobina Set": elem = Bobina(n_elem, "Set")
            elif tipo_elem == "Bobina Reset": elem = Bobina(n_elem, "Reset")
            elif tipo_elem == "Temporizador TON": elem = Temporizador(n_elem, "TON", 5)
            elif tipo_elem == "Temporizador TOF": elem = Temporizador(n_elem, "TOF", 3)
            elif tipo_elem == "Contador CTU": elem = Contador(n_elem, "CTU", 5)
            elif tipo_elem == "Contador CTD": elem = Contador(n_elem, "CTD", 5)
            elif tipo_elem == "Comparador": elem = Comparador(n_elem, ">", 50)
            
            st.session_state.rungs.append(Rung([c], elem))
            st.rerun()
            
    if st.button("🗑️ Borrar todo", use_container_width=True):
        st.session_state.rungs = []; st.session_state.evaluacion_actual = ""; st.rerun()

# =====================================================================
# 7. RUTA (Resumido igual que antes)
# =====================================================================
def cargar_practica(nivel):
    info = obtener_temario()[nivel]
    st.session_state.rungs = info['rungs']; st.session_state.entradas = info['entradas']
    st.session_state.nivel_actual = nivel; st.session_state.evaluacion_actual = ""
    st.session_state.main_tabs = "💻 Simulador Ladder"

def pedir_teoria(nivel):
    info = obtener_temario()[nivel]
    with st.spinner("Preparando clase..."):
        st.session_state.teoria_actual = generar_teoria_ia(info['titulo'], info['prompt_ia'])
        cargar_practica(nivel)

with tabs[1]:
    completadas = obtener_misiones_completadas(st.session_state.user.id)
    for nivel, info in obtener_temario().items():
        nom = f"Nivel {nivel}: {info['titulo']}"
        ya = nom in completadas
        desbloqueado = (nivel == 1) or (f"Nivel {nivel-1}: {obtener_temario()[nivel-1]['titulo']}" in completadas)
        if desbloqueado:
            with st.expander(f"{nom} {'✅' if ya else '📖'}", expanded=True):
                c1, c2 = st.columns(2)
                c1.button("🧠 Teoría IA", key=f"t_{nivel}", on_click=pedir_teoria, args=(nivel,))
                c2.button("💡 Ver Solución", key=f"p_{nivel}", type="primary", on_click=cargar_practica, args=(nivel,))
                if not ya:
                    if st.button("✅ Completar Nivel", key=f"c_{nivel}"):
                        exito, msg = agente_guardar_historial(st.session_state.user.id, 10, nom)
                        if exito: st.success("¡Guardado!"); time.sleep(1); st.rerun()
                        else: st.error(msg)
        else: st.warning(f"🔒 {nom} (Bloqueado)")

# =====================================================================
# 8. BIBLIOTECA (Ahora tiene TODOS los símbolos)
# =====================================================================
def pedir_explicacion(simbolo):
    with st.spinner("Generando explicación..."):
        st.session_state.explicacion_simbolo = explicar_simbolo_ia(simbolo)

with tabs[2]:
    st.subheader("Biblioteca de Símbolos Ladder Industriales")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='symbol-card'><b>Contacto NA</b><span class='symbol-icon'>—| |—</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b1", on_click=pedir_explicacion, args=("Contacto Normalmente Abierto",), use_container_width=True)
    with c2:
        st.markdown("<div class='symbol-card'><b>Contacto NC</b><span class='symbol-icon'>—|/|—</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b2", on_click=pedir_explicacion, args=("Contacto Normalmente Cerrado",), use_container_width=True)
    with c3:
        st.markdown("<div class='symbol-card'><b>Bobina</b><span class='symbol-icon'>—( )—</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b3", on_click=pedir_explicacion, args=("Bobina de salida normal",), use_container_width=True)
        
    st.divider()
    
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown("<div class='symbol-card'><b>Bobina Set/Reset</b><span class='symbol-icon'>—(S)— / —(R)—</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b4", on_click=pedir_explicacion, args=("Bobina Set y Reset",), use_container_width=True)
    with c5:
        st.markdown("<div class='symbol-card'><b>Flancos (P/N)</b><span class='symbol-icon'>—|P|— / —|N|—</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b5", on_click=pedir_explicacion, args=("Contactos de Flanco de subida y bajada",), use_container_width=True)
    with c6:
        st.markdown("<div class='symbol-card'><b>Temporizadores</b><span class='symbol-icon'>[ TON ] / [ TOF ]</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b6", on_click=pedir_explicacion, args=("Temporizadores TON y TOF",), use_container_width=True)

    st.divider()
    
    c7, c8, _ = st.columns(3)
    with c7:
        st.markdown("<div class='symbol-card'><b>Contadores</b><span class='symbol-icon'>[ CTU ] / [ CTD ]</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b7", on_click=pedir_explicacion, args=("Contadores CTU y CTD",), use_container_width=True)
    with c8:
        st.markdown("<div class='symbol-card'><b>Comparador</b><span class='symbol-icon'>[ > ] [ < ] [ == ]</span></div>", unsafe_allow_html=True)
        st.button("Explicar", key="b8", on_click=pedir_explicacion, args=("Comparadores numéricos",), use_container_width=True)

    if st.session_state.explicacion_simbolo:
        st.divider()
        st.info(f"🎓 **Tutor IA:**\n\n{st.session_state.explicacion_simbolo}")
        if st.button("Cerrar"): st.session_state.explicacion_simbolo = ""; st.rerun()

# =====================================================================
# 9. MI PERFIL Y ADMIN
# =====================================================================
with tabs[3]:
    with st.form("editar_perfil"):
        nuevo_nombre = st.text_input("Nombre de usuario", value=st.session_state.username)
        if st.form_submit_button("Actualizar Nombre", type="primary"):
            if nuevo_nombre:
                supabase.table("profiles").update({"username": nuevo_nombre}).eq("id", st.session_state.user.id).execute()
                st.session_state.username = nuevo_nombre; st.success("¡Actualizado!"); st.rerun()

if st.session_state.role == "admin":
    with tabs[4]:
        st.subheader("Centro de Control del Administrador")
        usuarios = admin_ver_todos_los_usuarios()
        if usuarios:
            df = pd.DataFrame(usuarios)
            edited_df = st.data_editor(df, use_container_width=True, column_config={"username": st.column_config.TextColumn("Nombre", required=True)}, hide_index=True)
            if st.button("💾 Guardar Cambios", type="primary"):
                for i, row in edited_df.iterrows():
                    supabase.table("profiles").update({"username": row["username"]}).eq("id", df.iloc[i]["id"]).execute()
                st.rerun()
        st.divider()
        st.dataframe(admin_ver_todo_el_progreso(), use_container_width=True)
