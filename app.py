import streamlit as st
import pandas as pd
import time
import google.generativeai as genai
from base_datos import conectar_supabase, agente_guardar_historial, obtener_misiones_completadas, admin_ver_todos_los_usuarios, admin_ver_todo_el_progreso
from logica_plc import Rung, Contacto, Bobina
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
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. CONEXIONES
# =====================================================================
supabase = conectar_supabase()

GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
else:
    st.warning("⚠️ Falta la GEMINI_API_KEY en los Secrets. Las funciones de IA estarán deshabilitadas.")

# =====================================================================
# 3. FUNCIONES DE IA
# =====================================================================
def generar_teoria_ia(tema, prompt):
    if not GEMINI_KEY: return "Falta la API Key de Gemini."
    try:
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        prompt_completo = f"Eres un instructor de PLC. El tema es '{tema}'. {prompt} Responde en máximo 2 párrafos, en español, de forma clara y directa."
        response = model.generate_content(prompt_completo)
        return response.text
    except Exception as e: return f"Error de IA: {e}"

def evaluar_codigo_ia(codigo_actual, nivel_actual):
    if not GEMINI_KEY: return "Falta la API Key de Gemini."
    try:
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        prompt = f"""
        Eres un profesor de PLC. El alumno está en el Nivel {nivel_actual}.
        Su código Ladder actual es: {codigo_actual}.
        Revisa si tiene errores lógicos (ej. falta el contacto auxiliar en paralelo para el enclavamiento, o puso mal un NC). Explícale de forma constructiva qué debe corregir en su Constructor de Ladder.
        Responde en máximo 2 párrafos.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Error: {e}"

# =====================================================================
# 4. ESTADO DE LA SESIÓN
# =====================================================================
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = "student"
    st.session_state.username = None
    st.session_state.rungs = []
    st.session_state.entradas = {"Start": False, "Stop": False}
    st.session_state.teoria_actual = ""
    st.session_state.evaluacion_actual = ""
    st.session_state.nivel_actual = 1

if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

tiempo_transcurrido = time.time() - st.session_state.start_time
minutos_restantes = max(0, 60 - int(tiempo_transcurrido // 60))

# =====================================================================
# 5. LOGIN Y NOMBRE
# =====================================================================
if st.session_state.user is None:
    st.title("⚙️ PLC Academy Pro")
    with st.form("login"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Iniciar Sesión", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                rol_query = supabase.table("user_roles").select("role").eq("user_id", res.user.id).execute()
                st.session_state.role = rol_query.data[0]["role"] if rol_query.data else "student"
                perfil_query = supabase.table("profiles").select("username").eq("id", res.user.id).execute()
                st.session_state.username = perfil_query.data[0].get("username") if perfil_query.data else None
                st.session_state.start_time = time.time() 
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    st.stop()

if st.session_state.username is None:
    st.info("¡Bienvenido! Por favor, dinos cómo te llamas.")
    with st.form("nombre_form"):
        nuevo_nombre = st.text_input("Tu nombre o apodo:")
        if st.form_submit_button("Guardar Nombre"):
            if nuevo_nombre:
                supabase.table("profiles").update({"username": nuevo_nombre}).eq("id", st.session_state.user.id).execute()
                st.session_state.username = nuevo_nombre
                st.rerun()
    st.stop()

# =====================================================================
# 6. CABECERA Y RELOJ
# =====================================================================
col_perfil, col_timer, col_logout = st.columns([6, 2, 2])
with col_perfil:
    badge_color = "#ff4b4b" if st.session_state.role == "admin" else "#007bff"
    rol_texto = "ADMINISTRADOR" if st.session_state.role == "admin" else "ESTUDIANTE"
    st.markdown(f"""
    <div class='profile-header'>
        <h2 style='margin: 0;'>👤 {st.session_state.username}</h2>
        <span style='background-color: {badge_color}; padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white;'>
            ROL: {rol_texto}
        </span>
    </div>
    """, unsafe_allow_html=True)
with col_timer:
    st.markdown(f"<div class='timer-box'>⏱️ Tiempo restante:<br><span style='font-size:24px; color:#00ff00;'>{minutos_restantes} min</span></div>", unsafe_allow_html=True)
with col_logout:
    if st.button("Cerrar Sesión", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

if minutos_restantes <= 0:
    st.error("🛑 ¡Tiempo de estudio completado por hoy!")
    if st.button("Saltar bloqueo (Para probar)"):
        st.session_state.start_time = time.time()
        st.rerun()
    st.stop()

# =====================================================================
# 7. PESTAÑAS
# =====================================================================
tabs_list = ["💻 Simulador Ladder", "🗺️ Ruta de Aprendizaje", "⚙️ Mi Perfil"]
if st.session_state.role == "admin":
    tabs_list.append("🛡️ Panel Admin")

tabs = st.tabs(tabs_list, key="main_tabs", on_change="rerun")

# =====================================================================
# 8. PESTAÑA 1: SIMULADOR Y CONSTRUCTOR
# =====================================================================
with tabs[0]:
    st.subheader("Entorno de Programación")
    
    if st.session_state.teoria_actual:
        st.info(f"📖 **Teoría:**\n\n{st.session_state.teoria_actual}")
            
    col_io, col_ladder = st.columns([1, 3])
    
    with col_io:
        st.markdown("### Panel I/O")
        st.write("*(Pulsadores momentáneos)*")
        for nombre in list(st.session_state.entradas.keys()):
            if nombre in ["Start", "Stop"]:
                if st.button(f"Pulsar {nombre}", key=f"btn_{nombre}", use_container_width=True):
                    st.session_state.entradas[nombre] = True
                else:
                    st.session_state.entradas[nombre] = False
            else:
                st.session_state.entradas[nombre] = st.toggle(nombre, value=st.session_state.entradas[nombre])
            
    with col_ladder:
        st.markdown("### Código Ladder")
        if not st.session_state.rungs:
            st.info("Usa el Constructor de abajo para escribir tu primer Rung.")
        else:
            dibujar_ladder(st.session_state.rungs, st.session_state.entradas)
            st.divider()
            dibujar_gemelo_digital(st.session_state.rungs)
            
            if st.button("🤖 Pedir al Tutor IA que evalúe mi código", type="secondary", use_container_width=True):
                codigo_resumen = []
                for i, r in enumerate(st.session_state.rungs):
                    contactos_desc = [f"{c.nombre}({c.tipo})" for c in r.contactos]
                    codigo_resumen.append(f"Rung {i+1}: [{ ' + '.join(contactos_desc) }] --- ( {r.bobina.nombre} )")
                codigo_str = " | ".join(codigo_resumen)
                with st.spinner("El Tutor IA está revisando tu lógica..."):
                    st.session_state.evaluacion_actual = evaluar_codigo_ia(codigo_str, st.session_state.nivel_actual)
            
            if st.session_state.evaluacion_actual:
                st.markdown(f"<div class='eval-box'>🎓 <b>Evaluación del Tutor IA:</b><br><br>{st.session_state.evaluacion_actual}</div>", unsafe_allow_html=True)

    # --- CONSTRUCTOR DE LADDER ---
    st.divider()
    st.markdown("### 🛠️ Constructor de Ladder (Escribe tu código aquí)")
    
    with st.form("ladder_builder"):
        col_b1, col_b2, col_b3 = st.columns(3)
        contacto_nombre = col_b1.text_input("Nombre del Contacto", value="Start")
        contacto_tipo = col_b2.selectbox("Tipo", ["NA", "NC"])
        bobina_nombre = col_b3.text_input("Nombre de la Bobina", value="Lamp")
        
        if st.form_submit_button("Añadir este Rung al Programa", type="primary"):
            nuevo_rung = Rung([Contacto(contacto_nombre, contacto_tipo)], Bobina(bobina_nombre))
            st.session_state.rungs.append(nuevo_rung)
            st.rerun()
            
    if st.button("🗑️ Borrar todo el código", use_container_width=True):
        st.session_state.rungs = []
        st.session_state.evaluacion_actual = ""
        st.rerun()

# =====================================================================
# 9. PESTAÑA 2: RUTA DE APRENDIZAJE
# =====================================================================
def cargar_practica(nivel):
    info = obtener_temario()[nivel]
    st.session_state.rungs = info['rungs']
    st.session_state.entradas = info['entradas']
    st.session_state.nivel_actual = nivel
    st.session_state.evaluacion_actual = ""
    st.session_state.main_tabs = "💻 Simulador Ladder"

def pedir_teoria(nivel):
    info = obtener_temario()[nivel]
    with st.spinner("El Tutor IA está preparando tu clase..."):
        st.session_state.teoria_actual = generar_teoria_ia(info['titulo'], info['prompt_ia'])
        cargar_practica(nivel)

with tabs[1]:
    st.subheader("Ruta de Aprendizaje Estructurada")
    
    completadas = obtener_misiones_completadas(st.session_state.user.id)
    temario = obtener_temario()
    
    for nivel, info in temario.items():
        nombre_mision = f"Nivel {nivel}: {info['titulo']}"
        ya_completada = nombre_mision in completadas
        desbloqueado = (nivel == 1) or (f"Nivel {nivel-1}: {temario[nivel-1]['titulo']}" in completadas)
        
        if desbloqueado:
            with st.expander(f"{nombre_mision} {'✅' if ya_completada else '📖'}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.button("🧠 Pedir Teoría al Tutor IA", key=f"teoria_{nivel}", on_click=pedir_teoria, args=(nivel,))
                with col2:
                    st.button("💡 Ver Solución (Cargar en Simulador)", key=f"prac_{nivel}", type="primary", on_click=cargar_practica, args=(nivel,))
                
                if not ya_completada:
                    if st.button("✅ Marcar Nivel como Completado", key=f"comp_{nivel}"):
                        agente_guardar_historial(st.session_state.user.id, 10, nombre_mision)
                        st.rerun()
                else:
                    st.success("¡Nivel completado!")
        else:
            st.warning(f"🔒 {nombre_mision} (Bloqueado)")

# =====================================================================
# 10. PESTAÑA 3: MI PERFIL
# =====================================================================
with tabs[2]:
    st.subheader("Configuración de Mi Perfil")
    with st.form("editar_perfil"):
        nuevo_nombre = st.text_input("Nombre de usuario", value=st.session_state.username)
        if st.form_submit_button("Actualizar Nombre", type="primary"):
            if nuevo_nombre:
                supabase.table("profiles").update({"username": nuevo_nombre}).eq("id", st.session_state.user.id).execute()
                st.session_state.username = nuevo_nombre
                st.success("¡Nombre actualizado!")
                st.rerun()

# =====================================================================
# 11. PESTAÑA 4: ADMINISTRADOR
# =====================================================================
if st.session_state.role == "admin":
    with tabs[3]:
        st.subheader("Centro de Control del Administrador")
        st.markdown("### 👥 Gestión de Usuarios")
        usuarios = admin_ver_todos_los_usuarios()
        if usuarios:
            df_usuarios = pd.DataFrame(usuarios)
            edited_df = st.data_editor(
                df_usuarios, use_container_width=True,
                column_config={
                    "username": st.column_config.TextColumn("Nombre de Usuario", required=True),
                    "xp": st.column_config.NumberColumn("XP", disabled=True),
                    "level": st.column_config.NumberColumn("Nivel", disabled=True)
                }, hide_index=True
            )
            if st.button("💾 Guardar Cambios de Usuarios", type="primary"):
                for index, row in edited_df.iterrows():
                    user_id = df_usuarios.iloc[index]["id"]
                    supabase.table("profiles").update({"username": row["username"]}).eq("id", user_id).execute()
                st.rerun()

        st.divider()
        st.markdown("### 📈 Historial de Progreso Global")
        progreso = admin_ver_todo_el_progreso()
        st.dataframe(progreso, use_container_width=True)
