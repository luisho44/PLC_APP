import streamlit as st
import os
import jwt
from supabase import create_client

# =====================================================================
# 1. CONFIGURACIÓN INICIAL
# =====================================================================
st.set_page_config(
    page_title="PLC Academy | Simulador",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ocultar menú de Streamlit
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# =====================================================================
# 2. CONEXIÓN A SUPABASE
# =====================================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Error: Credenciales no configuradas.")
    st.stop()

SUPABASE_URL = SUPABASE_URL.strip()
SUPABASE_KEY = SUPABASE_KEY.strip()
if not SUPABASE_URL.startswith("https://"):
    SUPABASE_URL = "https://" + SUPABASE_URL
if not SUPABASE_URL.endswith(".supabase.co"):
    SUPABASE_URL = SUPABASE_URL + ".supabase.co"

try:
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase = st.session_state.sb
except Exception as e:
    st.error(f"Error al conectar con Supabase: {e}")
    st.stop()

# =====================================================================
# 3. MODELO DE DATOS
# =====================================================================
class Contacto:
    def __init__(self, nombre, tipo="NA"):
        self.nombre = nombre
        self.tipo = tipo
    def evaluar(self, entradas):
        v = entradas.get(self.nombre, False)
        return v if self.tipo == "NA" else not v
    def to_dict(self):
        return {"nombre": self.nombre, "tipo": self.tipo}
    @classmethod
    def from_dict(cls, d):
        return cls(d["nombre"], d["tipo"])

class Bobina:
    def __init__(self, nombre):
        self.nombre = nombre
        self.estado = False
    def to_dict(self):
        return {"nombre": self.nombre}
    @classmethod
    def from_dict(cls, d):
        return cls(d["nombre"])

class Rung:
    def __init__(self, contactos, bobina):
        self.contactos = contactos
        self.bobina = bobina
    def evaluar(self, entradas):
        for c in self.contactos:
            if not c.evaluar(entradas):
                self.bobina.estado = False
                return
        self.bobina.estado = True
    def to_dict(self):
        return {"contactos": [c.to_dict() for c in self.contactos], "bobina": self.bobina.to_dict()}
    @classmethod
    def from_dict(cls, d):
        return cls([Contacto.from_dict(c) for c in d["contactos"]], Bobina.from_dict(d["bobina"]))

# =====================================================================
# 4. ESTADO DE LA SESIÓN
# =====================================================================
def init_state():
    defaults = {
        "user": None, 
        "user_role": "student", 
        "rungs": [], 
        "entradas": {"Start": False, "Stop": False, "Sensor": False},
        "current_project_id": None, 
        "current_project_name": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_state()

# =====================================================================
# 5. INTERFAZ DE AUTENTICACIÓN
# =====================================================================
def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>⚙️ PLC Academy</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Entorno de Simulación Ladder</p>", unsafe_allow_html=True)
        st.divider()

        with st.form("login_form"):
            email = st.text_input("Usuario (Email)")
            pw = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
            
            if submit and email and pw:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user
                    
                    try:
                        decoded = jwt.decode(res.session.access_token, options={"verify_signature": False})
                        st.session_state.user_role = decoded.get("user_role", "student")
                    except:
                        st.session_state.user_role = "student"
                        
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de acceso: {e}")

# =====================================================================
# 6. FUNCIONES DE BASE DE DATOS
# =====================================================================
def save_project(name):
    if not st.session_state.rungs:
        st.warning("El programa está vacío.")
        return
    data = {"rungs": [r.to_dict() for r in st.session_state.rungs], "entradas": st.session_state.entradas}
    try:
        if st.session_state.current_project_id:
            supabase.table("projects").update({"name": name, "program_data": data}).eq("id", st.session_state.current_project_id).execute()
            st.success(f"Proyecto '{name}' actualizado.")
        else:
            res = supabase.table("projects").insert({"user_id": st.session_state.user.id, "name": name, "program_data": data}).execute()
            st.session_state.current_project_id = res.data[0]["id"]
            st.success(f"Proyecto '{name}' guardado.")
        st.session_state.current_project_name = name
    except Exception as e:
        st.error(f"Error al guardar: {e}")

def list_projects():
    try:
        res = supabase.table("projects").select("id,name,updated_at").order("updated_at", desc=True).execute()
        return res.data
    except Exception:
        return []

def load_project(pid):
    try:
        res = supabase.table("projects").select("*").eq("id", pid).single().execute()
        p = res.data
        d = p["program_data"]
        st.session_state.rungs = [Rung.from_dict(r) for r in d.get("rungs", [])]
        st.session_state.entradas = d.get("entradas", {})
        st.session_state.current_project_id = p["id"]
        st.session_state.current_project_name = p["name"]
        st.success(f"Proyecto '{p['name']}' cargado.")
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

def delete_project(pid):
    try:
        supabase.table("projects").delete().eq("id", pid).execute()
        if st.session_state.current_project_id == pid:
            st.session_state.current_project_id = None
            st.session_state.current_project_name = None
        st.success("Proyecto eliminado.")
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# =====================================================================
# 7. INTERFAZ DEL SIMULADOR (IDÉNTICO AL ANTERIOR)
# =====================================================================
def show_simulator():
    st.subheader("Panel de Control (I/O)")
    
    cols = st.columns(len(st.session_state.entradas))
    for i, nombre in enumerate(list(st.session_state.entradas.keys())):
        with cols[i]:
            st.session_state.entradas[nombre] = st.toggle(nombre, value=st.session_state.entradas[nombre], key=f"tog_{nombre}")

    with st.expander("Configurar Entradas"):
        col1, col2 = st.columns([4, 1])
        with col1:
            nueva = st.text_input("Nombre de la entrada", key="new_in", label_visibility="collapsed", placeholder="Ej: Sensor_Nivel")
        with col2:
            if st.button("Añadir Entrada", use_container_width=True) and nueva:
                if nueva not in st.session_state.entradas:
                    st.session_state.entradas[nueva] = False
                    st.rerun()

    st.divider()
    st.subheader("Editor de Lógica (Rungs)")
    
    with st.expander("Añadir nuevo Rung"):
        num = st.number_input("Cantidad de contactos en serie", 1, 5, 1, key="num_c")
        contactos = []
        for i in range(int(num)):
            c1, c2 = st.columns([3, 1])
            with c1:
                nom = st.text_input(f"Contacto {i+1}", value="Start", key=f"n_{i}")
            with c2:
                tipo = st.selectbox("Tipo", ["NA", "NC"], key=f"t_{i}")
            contactos.append(Contacto(nom, tipo))
        bob = st.text_input("Bobina (Salida)", value="Lamp", key="bob_name")
        
        if st.button("Insertar Rung", use_container_width=True, type="primary"):
            st.session_state.rungs.append(Rung(contactos, Bobina(bob)))
            st.rerun()

    st.divider()
    
    if not st.session_state.rungs:
        st.info("No hay lógica programada. Añade un Rung para comenzar.")
        return

    for r in st.session_state.rungs:
        r.evaluar(st.session_state.entradas)

    for i, rung in enumerate(st.session_state.rungs):
        with st.container(border=True):
            col_del, col_rung = st.columns([1, 15])
            with col_del:
                if st.button("X", key=f"del_{i}", help="Eliminar Rung"):
                    st.session_state.rungs.pop(i)
                    st.rerun()
            
            with col_rung:
                partes = []
                for c in rung.contactos:
                    v = st.session_state.entradas.get(c.nombre, False)
                    if c.tipo == "NA":
                        estado = "| |" if not v else "|‾|"
                    else:
                        estado = "|/|" if not v else "| |"
                    partes.append(f"[ {estado} {c.nombre} ]")
                
                bobina_str = f"( {rung.bobina.nombre} )"
                estado_bob = "ACTIVO" if rung.bobina.estado else "INACTIVO"
                color_bob = "green" if rung.bobina.estado else "red"
                
                linea_logica = " --- ".join(partes)
                st.markdown(f"**{linea_logica} --- {bobina_str}** &nbsp;&nbsp;&nbsp; <span style='color:{color_bob}; font-weight:bold;'>{estado_bob}</span>", unsafe_allow_html=True)

    st.divider()
    with st.expander("Gestión de Archivo"):
        default_name = st.session_state.current_project_name or ""
        nombre = st.text_input("Nombre del archivo", value=default_name, key="save_name")
        if st.button("Guardar Programa", use_container_width=True, type="primary"):
            if nombre:
                save_project(nombre)
            else:
                st.warning("Asigne un nombre al archivo.")

# =====================================================================
# 8. INTERFAZ DE PROYECTOS
# =====================================================================
def show_projects():
    st.subheader("Repositorio de Proyectos")
    proyectos = list_projects()
    if not proyectos:
        st.info("No hay proyectos guardados.")
        return
    
    for p in proyectos:
        with st.container(border=True):
            col1, col2, col3 = st.columns([6, 2, 2])
            with col1:
                st.markdown(f"**{p['name']}**")
                st.caption(f"Última modificación: {p['updated_at'][:10]}")
            with col2:
                if st.button("Abrir", key=f"ld_{p['id']}", use_container_width=True):
                    load_project(p["id"])
            with col3:
                if st.button("Eliminar", key=f"dl_{p['id']}", use_container_width=True):
                    delete_project(p["id"])

# =====================================================================
# 9. INTERFAZ DE PROGRESO
# =====================================================================
def show_progress():
    st.subheader("Estadísticas del Usuario")
    try:
        res = supabase.table("profiles").select("xp,level").eq("id", st.session_state.user.id).single().execute()
        prof = res.data or {}
    except Exception:
        prof = {}
    
    col1, col2 = st.columns(2)
    col1.metric("Puntos de Experiencia (XP)", prof.get("xp", 0))
    col2.metric("Nivel de Operador", prof.get("level", 1))
    st.info("Módulo de evaluaciones en desarrollo.")

# =====================================================================
# 10. NUEVA INTERFAZ DE ACADEMIA (EJEMPLOS)
# =====================================================================
def show_academy():
    st.subheader("Módulo de Aprendizaje")
    st.write("Selecciona un ejemplo para cargarlo automáticamente en el simulador y ver cómo funciona.")

    # Lección 1: Enclavamiento
    with st.container(border=True):
        st.markdown("### Lección 1: Circuito de Enclavamiento (Self-Holding)")
        st.write("""
        **Objetivo:** Aprender a mantener encendida una salida (Lamp) después de soltar un pulsador momentáneo.
        
        **Lógica:** 
        1. Al presionar **Start**, la energía pasa al contacto NA y llega a la bobina.
        2. Cuando la bobina se enciende, cierra un contacto NA en paralelo con el Start original.
        3. Si sueltas **Start**, la energía sigue pasando por el contacto paralelo.
        4. Para apagar la lámpara, debes presionar **Stop**, que es un contacto NC y rompe el circuito.
        """)
        
        if st.button("Cargar Ejemplo en Simulador", key="load_ex1", type="primary"):
            # Forzamos las entradas necesarias
            st.session_state.entradas["Start"] = False
            st.session_state.entradas["Stop"] = False
            
            # Rung 1: El Start original
            rung1 = Rung([Contacto("Start", "NA")], Bobina("Lamp"))
            
            # Rung 2: El enclavamiento (Lamp en paralelo con Start, y el Stop en serie)
            rung2 = Rung([Contacto("Lamp", "NA"), Contacto("Stop", "NC")], Bobina("Lamp"))
            
            st.session_state.rungs = [rung1, rung2]
            st.success("Ejemplo cargado. Ve a la pestaña 'Entorno Ladder' y activa el Start.")
            st.rerun()

    # Aquí puedes agregar más lecciones (Lección 2, Lección 3, etc.) en el futuro.

# =====================================================================
# 11. PANTALLA PRINCIPAL (DASHBOARD)
# =====================================================================
def show_main():
    st.markdown("<h2>PLC Academy - Entorno de Desarrollo</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([8, 2])
    with col1:
        rol = "ADMINISTRADOR" if st.session_state.user_role == "admin" else "ESTUDIANTE"
        st.markdown(f"**Usuario:** {st.session_state.user.email} &nbsp;|&nbsp; **Rol:** `{rol}`")
    with col2:
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            for k in list(st.session_state.keys()):
                if k != "sb": del st.session_state[k]
            st.rerun()
            
    st.divider()
    
    # Añadimos la pestaña Academia
    tab_sim, tab_acad, tab_proj, tab_prog = st.tabs(["Entorno Ladder", "Academia", "Proyectos", "Métricas"])
    
    with tab_sim: show_simulator()
    with tab_acad: show_academy()
    with tab_proj: show_projects()
    with tab_prog: show_progress()

# =====================================================================
# 12. ENRUTADOR
# =====================================================================
if st.session_state.user is None:
    show_login()
else:
    show_main()
