import streamlit as st
import pandas as pd
from base_datos import (
    conectar_supabase, agente_guardar_historial, 
    admin_ver_todos_los_usuarios, admin_ver_todo_el_progreso,
    obtener_misiones_completadas
)
from logica_plc import Rung, Contacto, Bobina
from interfaz import dibujar_ladder, dibujar_gemelo_digital
from misiones import obtener_misiones

st.set_page_config(page_title="PLC Academy Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0e1117; }
    .profile-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

supabase = conectar_supabase()

# Inicializar estado
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = "student"
    st.session_state.username = None
    st.session_state.rungs = []
    st.session_state.entradas = {"Start": False, "Stop": False}

if "role" not in st.session_state:
    st.session_state.role = "student"

# --- LOGIN ---
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
                
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    st.stop()

# --- PEDIR NOMBRE ---
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

# --- CABECERA ---
col_perfil, col_logout = st.columns([9, 1])
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
with col_logout:
    if st.button("Cerrar Sesión", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# --- PESTAÑAS ---
tabs_list = ["💻 Simulador Ladder", "📚 Aprender a Programar", "⚙️ Mi Perfil"]
if st.session_state.role == "admin":
    tabs_list.append("🛡️ Panel de Administrador")

tabs = st.tabs(tabs_list)

# --- PESTAÑA 1: SIMULADOR ---
with tabs[0]:
    st.subheader("Entorno de Programación (IEC 61131-3)")
    col_io, col_ladder = st.columns([1, 3])
    
    with col_io:
        st.markdown("### Panel I/O")
        for nombre in list(st.session_state.entradas.keys()):
            st.session_state.entradas[nombre] = st.toggle(nombre, value=st.session_state.entradas[nombre])
            
    with col_ladder:
        st.markdown("### Código Ladder")
        if not st.session_state.rungs:
            st.info("Carga un ejemplo en la pestaña 'Aprender'.")
        else:
            dibujar_ladder(st.session_state.rungs, st.session_state.entradas)
            st.divider()
            dibujar_gemelo_digital(st.session_state.rungs)

    with st.expander("Herramienta de Programación (Añadir Rung)"):
        with st.form("add_rung"):
            c1, c2, c3 = st.columns(3)
            nombre_c = c1.text_input("Contacto", value="Start")
            tipo_c = c2.selectbox("Tipo", ["NA", "NC"])
            nombre_b = c3.text_input("Bobina", value="Lamp")
            if st.form_submit_button("Insertar en Ladder"):
                st.session_state.rungs.append(Rung([Contacto(nombre_c, tipo_c)], Bobina(nombre_b)))
                st.rerun()

# --- PESTAÑA 2: APRENDER ---
with tabs[1]:
    st.subheader("Módulos de Aprendizaje")
    
    # El agente revisa qué misiones tienes completadas
    completadas = obtener_misiones_completadas(supabase, st.session_state.user.id)
    misiones_orden = list(obtener_misiones().keys())
    
    # Lógica de desbloqueo del Agente
    for i, key in enumerate(misiones_orden):
        mision = obtener_misiones()[key]
        
        # La misión 1 siempre está desbloqueada. Las demás dependen de la anterior.
        desbloqueada = (i == 0) or (misiones_orden[i-1] in completadas)
        
        if desbloqueada:
            with st.expander(f"{key}: {mision['titulo']}", expanded=True):
                st.write(mision['descripcion'])
                if st.button(f"Cargar {key}", key=f"load_{key}"):
                    st.session_state.rungs = mision['rungs']
                    st.session_state.entradas = mision['entradas']
                    st.success("Misión cargada en el Simulador.")
                    st.rerun()
                
                if key not in completadas:
                    if st.button(f"✅ Completar {key}", key=f"comp_{key}", type="primary"):
                        agente_guardar_historial(supabase, st.session_state.user.id, mision['xp'], key)
                        st.success(f"¡Misión guardada! Has ganado {mision['xp']} XP.")
                        st.rerun()
                else:
                    st.success("Misión ya completada. ¡Buen trabajo!")
        else:
            st.warning(f"🔒 {key} bloqueada. Completa la anterior para desbloquearla.")

# --- PESTAÑA 3: MI PERFIL ---
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

# --- PESTAÑA 4: ADMINISTRADOR ---
if st.session_state.role == "admin":
    with tabs[3]:
        st.subheader("Centro de Control del Administrador")
        
        st.markdown("### 👥 Gestión de Usuarios")
        usuarios = admin_ver_todos_los_usuarios(supabase)
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
                    # Buscamos por ID para que no falle si cambian el nombre
                    user_id = df_usuarios.iloc[index]["id"]
                    supabase.table("profiles").update({"username": row["username"]}).eq("id", user_id).execute()
                st.success("¡Nombres actualizados!")
                st.rerun()

        st.divider()
        st.markdown("### 📈 Historial de Progreso Global")
        progreso = admin_ver_todo_el_progreso(supabase)
        st.dataframe(progreso, use_container_width=True)
