import streamlit as st
from base_datos import conectar_supabase, agente_guardar_historial, admin_ver_todos_los_usuarios, admin_ver_todo_el_progreso
from logica_plc import Rung, Contacto, Bobina
from interfaz import dibujar_ladder, dibujar_gemelo_digital

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
                
                # 1. Obtener el rol
                rol_query = supabase.table("user_roles").select("role").eq("user_id", res.user.id).execute()
                st.session_state.role = rol_query.data[0]["role"] if rol_query.data else "student"
                
                # 2. Obtener el nombre de usuario desde la tabla profiles
                perfil_query = supabase.table("profiles").select("username").eq("id", res.user.id).execute()
                if perfil_query.data and perfil_query.data[0].get("username"):
                    st.session_state.username = perfil_query.data[0]["username"]
                else:
                    st.session_state.username = None 
                
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    st.stop()

# --- PEDIR NOMBRE DE USUARIO SI NO EXISTE ---
if st.session_state.username is None:
    st.info("¡Bienvenido a PLC Academy! Por favor, dinos cómo te llamas para personalizar tu experiencia.")
    with st.form("nombre_form"):
        nuevo_nombre = st.text_input("Tu nombre o apodo:")
        if st.form_submit_button("Guardar Nombre"):
            if nuevo_nombre:
                supabase.table("profiles").update({"username": nuevo_nombre}).eq("id", st.session_state.user.id).execute()
                st.session_state.username = nuevo_nombre
                st.success(f"¡Bienvenido, {nuevo_nombre}!")
                st.rerun()
    st.stop()

# --- CABECERA DEL PERFIL ---
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

# --- PESTAÑAS DEPENDIENDO DEL ROL ---
tabs_list = ["💻 Simulador Ladder", "📚 Aprender a Programar", "⚙️ Mi Perfil"]
if st.session_state.role == "admin":
    tabs_list.append("🛡️ Panel de Administrador")

tabs = st.tabs(tabs_list)

# --- PESTAÑA 1: SIMULADOR Y GEMELO DIGITAL ---
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
            st.info("Carga un ejemplo en la pestaña 'Aprender' o escribe tu propio código abajo.")
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
                st.session_state.rungs.append(
                    Rung([Contacto(nombre_c, tipo_c)], Bobina(nombre_b))
                )
                st.rerun()

# --- PESTAÑA 2: APRENDER ---
with tabs[1]:
    st.subheader("Módulos de Aprendizaje")
    st.write("Completa las misiones para que el sistema registre tu avance.")
    
    with st.expander("Misión 1: Encender una Lámpara (Lógica Básica)"):
        st.write("Activa el interruptor Start y observa cómo la lámpara del Gemelo Digital se enciende en tiempo real.")
        if st.button("Cargar Misión 1"):
            st.session_state.rungs = [Rung([Contacto("Start", "NA")], Bobina("Lamp"))]
            st.session_state.entradas = {"Start": False}
            st.rerun()
            
    with st.expander("Misión 2: Arrancar un Motor (Enclavamiento)"):
        st.write("Activa Start, suelta Start (el motor debe seguir girando). Presiona Stop para apagarlo.")
        if st.button("Cargar Misión 2"):
            st.session_state.rungs = [
                Rung([Contacto("Start", "NA")], Bobina("Motor")),
                Rung([Contacto("Motor", "NA"), Contacto("Stop", "NC")], Bobina("Motor"))
            ]
            st.session_state.entradas = {"Start": False, "Stop": False}
            st.rerun()

    if st.button("✅ Marcar Misión como Completada", type="primary"):
        agente_guardar_historial(supabase, st.session_state.user.id, 10, "Misión Completada")
        st.success("¡Progreso guardado en la base de datos de Supabase!")

# --- PESTAÑA 3: MI PERFIL ---
with tabs[2]:
    st.subheader("Configuración de Mi Perfil")
    st.write("Aquí puedes actualizar tu nombre de usuario.")
    
    with st.form("editar_perfil"):
        nuevo_nombre = st.text_input("Nombre de usuario", value=st.session_state.username)
        if st.form_submit_button("Actualizar Nombre", type="primary"):
            if nuevo_nombre:
                supabase.table("profiles").update({"username": nuevo_nombre}).eq("id", st.session_state.user.id).execute()
                st.session_state.username = nuevo_nombre
                st.success("¡Nombre actualizado con éxito!")
                st.rerun()

# --- PESTAÑA 4: PANEL DE ADMINISTRADOR ---
if st.session_state.role == "admin":
    with tabs[3]:
        st.subheader("Centro de Control del Administrador")
        st.write("Acceso exclusivo para instructores. Puedes modificar los nombres de los usuarios aquí.")
        
        # --- GESTIÓN DE USUARIOS (NUEVO) ---
        st.markdown("### 👥 Gestión de Usuarios")
        usuarios = admin_ver_todos_los_usuarios(supabase)
        
        if usuarios:
            # Convertimos la lista de diccionarios a un formato que Streamlit pueda editar
            import pandas as pd
            df_usuarios = pd.DataFrame(usuarios)
            
            # st.data_editor permite editar la tabla como en Excel
            edited_df = st.data_editor(
                df_usuarios, 
                use_container_width=True,
                column_config={
                    "username": st.column_config.TextColumn("Nombre de Usuario", required=True),
                    "xp": st.column_config.NumberColumn("XP", disabled=True),
                    "level": st.column_config.NumberColumn("Nivel", disabled=True)
                },
                hide_index=True
            )
            
            if st.button("💾 Guardar Cambios de Usuarios", type="primary"):
                for index, row in edited_df.iterrows():
                    # Actualizamos cada fila en Supabase
                    supabase.table("profiles").update({
                        "username": row["username"]
                    }).eq("username", df_usuarios.iloc[index]["username"]).execute()
                st.success("¡Nombres actualizados en la base de datos!")
                st.rerun()
        else:
            st.info("No hay usuarios registrados.")

        st.divider()
        
        # --- HISTORIAL DE PROGRESO ---
        st.markdown("### 📈 Historial de Progreso Global")
        progreso = admin_ver_todo_el_progreso(supabase)
        st.dataframe(progreso, use_container_width=True)
