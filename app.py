import streamlit as st
import pandas as pd
from supabase import create_client

# =====================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =====================================================================
st.set_page_config(page_title="PLC Academy Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0e1117; }
    .profile-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. CONEXIÓN A SUPABASE
# =====================================================================
@st.cache_resource
def init_supabase():
    URL = st.secrets.get("SUPABASE_URL", "")
    KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
    return create_client(URL, KEY)

supabase = init_supabase()

# =====================================================================
# 3. MODELO LADDER (Clases)
# =====================================================================
class Contacto:
    def __init__(self, nombre, tipo="NA"):
        self.nombre = nombre; self.tipo = tipo
    def evaluar(self, entradas):
        v = entradas.get(self.nombre, False)
        return v if self.tipo == "NA" else not v

class Bobina:
    def __init__(self, nombre): 
        self.nombre = nombre; self.estado = False

class Rung:
    def __init__(self, contactos, bobina):
        self.contactos = contactos; self.bobina = bobina
    def evaluar(self, entradas):
        for c in self.contactos:
            if not c.evaluar(entradas):
                self.bobina.estado = False; return
        self.bobina.estado = True

# =====================================================================
# 4. FUNCIONES DE BASE DE DATOS Y AGENTE
# =====================================================================
def agente_guardar_historial(user_id, minutos, mision):
    try:
        supabase.table("progreso_historico").insert({
            "user_id": user_id, "minutos_estudiados": minutos, "mision_completada": mision
        }).execute()
    except Exception as e:
        st.error(f"Error guardando: {e}")

def obtener_misiones_completadas(user_id):
    try:
        res = supabase.table("progreso_historico").select("mision_completada").eq("user_id", user_id).execute()
        return [item["mision_completada"] for item in res.data]
    except:
        return []

def admin_ver_todos_los_usuarios():
    try:
        return supabase.table("profiles").select("id, username, xp, level").execute().data
    except:
        return []

def admin_ver_todo_el_progreso():
    try:
        return supabase.table("progreso_historico").select("*").order("fecha", desc=True).execute().data
    except:
        return []

# =====================================================================
# 5. DICCIONARIO DE MISIONES (El Agente las usará)
# =====================================================================
def obtener_misiones():
    return {
        "Misión 1": {
            "titulo": "Encender una Lámpara",
            "descripcion": "Activa el interruptor Start y observa cómo la lámpara del Gemelo Digital se enciende en tiempo real.",
            "rungs": [Rung([Contacto("Start", "NA")], Bobina("Lamp"))],
            "entradas": {"Start": False},
            "xp": 10
        },
        "Misión 2": {
            "titulo": "Arrancar un Motor (Enclavamiento)",
            "descripcion": "Activa Start, suelta Start (el motor debe seguir girando). Presiona Stop para apagarlo.",
            "rungs": [
                Rung([Contacto("Start", "NA")], Bobina("Motor")),
                Rung([Contacto("Motor", "NA"), Contacto("Stop", "NC")], Bobina("Motor"))
            ],
            "entradas": {"Start": False, "Stop": False},
            "xp": 15
        },
        "Misión 3": {
            "titulo": "Lógica AND (Seguridad)",
            "descripcion": "La máquina solo enciende si el Operador presiona Start Y el Sensor está activo.",
            "rungs": [Rung([Contacto("Start", "NA"), Contacto("Sensor", "NA")], Bobina("Lamp"))],
            "entradas": {"Start": False, "Sensor": False},
            "xp": 20
        }
    }

# =====================================================================
# 6. FUNCIONES DE DIBUJO (Interfaz gráfica)
# =====================================================================
def dibujar_ladder(rungs, entradas):
    for rung in rungs:
        rung.evaluar(entradas)
        html = "<div style='border-left: 4px solid #00ff00; border-right: 4px solid #00ff00; padding: 20px; margin: 10px 0; background-color: #1a1c24; display: flex; align-items: center;'>"
        for c in rung.contactos:
            v = entradas.get(c.nombre, False)
            activo = v if c.tipo == "NA" else not v
            color = "#00ff00" if activo else "#555"
            simbolo = "| |" if activo else "|/|"
            html += f"<span style='border: 2px solid {color}; padding: 8px 15px; margin: 0 5px; color: {color}; font-weight: bold; font-family: monospace; border-radius: 5px;'>{c.nombre} {simbolo}</span>"
            html += "<span style='color: #555;'>———</span>"
        color_bob = "#00ff00" if rung.bobina.estado else "#555"
        bg_bob = "rgba(0, 255, 0, 0.2)" if rung.bobina.estado else "transparent"
        html += f"<span style='border: 2px solid {color_bob}; background-color: {bg_bob}; border-radius: 20px; padding: 8px 20px; margin-left: 10px; color: {color_bob}; font-weight: bold; font-family: monospace;'> ( {rung.bobina.nombre} ) </span>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

def dibujar_gemelo_digital(rungs):
    st.markdown("### Panel de Planta (Gemelo Digital)")
    col1, col2 = st.columns(2)
    lampara_encendida = any(r.bobina.nombre == "Lamp" and r.bobina.estado for r in rungs)
    motor_encendido = any(r.bobina.nombre == "Motor" and r.bobina.estado for r in rungs)
    
    with col1:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Lámpara de Planta</h3>", unsafe_allow_html=True)
            if lampara_encendida:
                st.markdown("<h1 style='text-align: center; font-size: 80px;'>💡</h1>", unsafe_allow_html=True)
                st.success("ESTADO: ENCENDIDA (220V)")
            else:
                st.markdown("<h1 style='text-align: center; font-size: 80px; filter: grayscale(100%); opacity: 0.3;'>💡</h1>", unsafe_allow_html=True)
                st.info("ESTADO: APAGADA")
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Motor de Inducción</h3>", unsafe_allow_html=True)
            if motor_encendido:
                st.markdown("<h1 style='text-align: center; font-size: 80px;'>⚙️</h1>", unsafe_allow_html=True)
                st.success("ESTADO: GIRANDO (1750 RPM)")
            else:
                st.markdown("<h1 style='text-align: center; font-size: 80px; filter: grayscale(100%); opacity: 0.3;'>⚙️</h1>", unsafe_allow_html=True)
                st.info("ESTADO: DETENIDO")

# =====================================================================
# 7. ESTADO DE LA SESIÓN
# =====================================================================
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = "student"
    st.session_state.username = None
    st.session_state.rungs = []
    st.session_state.entradas = {"Start": False, "Stop": False}

if "role" not in st.session_state:
    st.session_state.role = "student"

# =====================================================================
# 8. INTERFAZ DE LOGIN
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
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    st.stop()

# =====================================================================
# 9. PEDIR NOMBRE DE USUARIO
# =====================================================================
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
# 10. CABECERA DEL PERFIL
# =====================================================================
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

# =====================================================================
# 11. PESTAÑAS PRINCIPALES
# =====================================================================
tabs_list = ["💻 Simulador Ladder", "📚 Aprender a Programar", "⚙️ Mi Perfil"]
if st.session_state.role == "admin":
    tabs_list.append("🛡️ Panel de Administrador")

tabs = st.tabs(tabs_list)

# =====================================================================
# 12. PESTAÑA 1: SIMULADOR LADDER
# =====================================================================
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

# =====================================================================
# 13. PESTAÑA 2: APRENDER (El Agente en acción)
# =====================================================================
with tabs[1]:
    st.subheader("Módulos de Aprendizaje")
    
    completadas = obtener_misiones_completadas(st.session_state.user.id)
    misiones = obtener_misiones()
    misiones_orden = list(misiones.keys())
    
    for i, key in enumerate(misiones_orden):
        mision = misiones[key]
        
        # Lógica de desbloqueo
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
                        agente_guardar_historial(st.session_state.user.id, mision['xp'], key)
                        st.success(f"¡Misión guardada! Has ganado {mision['xp']} XP.")
                        st.rerun()
                else:
                    st.success("Misión ya completada. ¡Buen trabajo!")
        else:
            st.warning(f"🔒 {key} bloqueada. Completa la anterior para desbloquearla.")

# =====================================================================
# 14. PESTAÑA 3: MI PERFIL
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
# 15. PESTAÑA 4: ADMINISTRADOR
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
                st.success("¡Nombres actualizados!")
                st.rerun()

        st.divider()
        st.markdown("### 📈 Historial de Progreso Global")
        progreso = admin_ver_todo_el_progreso()
        st.dataframe(progreso, use_container_width=True)
