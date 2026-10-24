import streamlit as st
import os
import jwt
from supabase import create_client

# =====================================================================
# 1. CONFIGURACIÓN INICIAL DE LA PÁGINA
# =====================================================================
st.set_page_config(
    page_title="PLC Academy",
    page_icon="🔌",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =====================================================================
# 2. CONEXIÓN A SUPABASE (CON VALIDACIÓN ESTRICTA)
# =====================================================================
# Intentamos leer las credenciales desde los Secrets de Streamlit
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")

# Validación 1: ¿Están vacías?
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Error: Faltan las credenciales de Supabase en los Secrets de Streamlit.")
    st.stop()

# Validación 2: Limpiamos la URL por si tiene espacios accidentales
SUPABASE_URL = SUPABASE_URL.strip()
SUPABASE_KEY = SUPABASE_KEY.strip()

# Validación 3: Aseguramos que la URL tenga el formato correcto (https y el dominio)
if not SUPABASE_URL.startswith("https://"):
    SUPABASE_URL = "https://" + SUPABASE_URL
if not SUPABASE_URL.endswith(".supabase.co"):
    SUPABASE_URL = SUPABASE_URL + ".supabase.co"

# Creamos el cliente (protegido por si falla la red)
try:
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase = st.session_state.sb
except Exception as e:
    st.error(f"Error crítico al conectar con Supabase: {e}")
    st.info("Verifica que la URL y la KEY sean correctas.")
    st.stop()


# =====================================================================
# 3. MODELO DE DATOS PARA LADDER (Contactos, Bobinas y Rungs)
# =====================================================================
class Contacto:
    def __init__(self, nombre, tipo="NA"):
        self.nombre = nombre
        self.tipo = tipo # "NA" (Normal Abierto) o "NC" (Normal Cerrado)
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
        self.estado = False # ON/OFF
    def to_dict(self):
        return {"nombre": self.nombre}
    @classmethod
    def from_dict(cls, d):
        return cls(d["nombre"])

class Rung:
    def __init__(self, contactos, bobina):
        self.contactos = contactos # Lista de contactos en serie
        self.bobina = bobina
    def evaluar(self, entradas):
        # Lógica AND: si todos los contactos se cumplen, la bobina se enciende
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
# 4. ESTADO DE LA SESIÓN (Para no perder datos al recargar)
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
# 5. INTERFAZ DE AUTENTICACIÓN (Login y Registro)
# =====================================================================
def show_login():
    st.markdown("# 🔌 PLC Academy")
    st.caption("Aprende Ladder Logic desde tu celular")
    st.divider()
    
    tab_login, tab_reg = st.tabs(["🔑 Iniciar sesión", "✨ Crear cuenta"])

    # Pestaña de Login
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("📧 Email")
            pw = st.text_input("🔒 Contraseña", type="password")
            ok = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            if ok and email and pw:
                try:
                    # Autenticación con Supabase
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user
                    
                    # Decodificamos el token JWT para leer el rol (admin/student)
                    try:
                        decoded = jwt.decode(res.session.access_token, options={"verify_signature": False})
                        st.session_state.user_role = decoded.get("user_role", "student")
                    except:
                        st.session_state.user_role = "student"
                        
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al iniciar sesión: {e}")

    # Pestaña de Registro
    with tab_reg:
        with st.form("reg_form"):
            email = st.text_input("📧 Email", key="r_email")
            pw = st.text_input("🔒 Contraseña (mín. 6 caract.)", type="password", key="r_pw")
            ok = st.form_submit_button("Crear cuenta", use_container_width=True, type="primary")
            if ok and email and pw:
                try:
                    # Registro en Supabase (con opción de no pedir confirmación por correo)
                    supabase.auth.sign_up({"email": email, "password": pw})
                    st.success("✅ Cuenta creada exitosamente. Ahora ve a la pestaña 'Iniciar sesión'.")
                except Exception as e:
                    st.error(f"❌ Error al crear cuenta: {e}")


# =====================================================================
# 6. FUNCIONES DE BASE DE DATOS (Guardar, cargar y borrar proyectos)
# =====================================================================
def save_project(name):
    if not st.session_state.rungs:
        st.warning("No hay rungs para guardar.")
        return
    data = {"rungs": [r.to_dict() for r in st.session_state.rungs], "entradas": st.session_state.entradas}
    try:
        if st.session_state.current_project_id:
            # Actualizar proyecto existente
            supabase.table("projects").update({"name": name, "program_data": data}).eq("id", st.session_state.current_project_id).execute()
            st.success(f"💾 Proyecto '{name}' actualizado")
        else:
            # Crear nuevo proyecto
            res = supabase.table("projects").insert({"user_id": st.session_state.user.id, "name": name, "program_data": data}).execute()
            st.session_state.current_project_id = res.data[0]["id"]
            st.success(f"💾 Proyecto '{name}' guardado")
        st.session_state.current_project_name = name
    except Exception as e:
        st.error(f"Error al guardar: {e}")

def list_projects():
    try:
        # Trae los proyectos del usuario actual, ordenados por fecha
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
        st.success(f"📂 '{p['name']}' cargado")
        st.rerun()
    except Exception as e:
        st.error(f"Error al cargar: {e}")

def delete_project(pid):
    try:
        supabase.table("projects").delete().eq("id", pid).execute()
        if st.session_state.current_project_id == pid:
            st.session_state.current_project_id = None
            st.session_state.current_project_name = None
        st.success("🗑️ Proyecto eliminado")
        st.rerun()
    except Exception as e:
        st.error(f"Error al eliminar: {e}")


# =====================================================================
# 7. INTERFAZ DEL SIMULADOR (Entradas y Rungs)
# =====================================================================
def show_simulator():
    st.markdown("### 🎛️ Panel de Entradas")
    
    # Mostramos un interruptor (toggle) por cada entrada
    for nombre in list(st.session_state.entradas.keys()):
        st.session_state.entradas[nombre] = st.toggle(
            f"**{nombre}**", 
            value=st.session_state.entradas[nombre], 
            key=f"tog_{nombre}"
        )

    # Añadir nuevas entradas
    with st.expander("➕ Añadir entrada"):
        col1, col2 = st.columns([3, 1])
        with col1:
            nueva = st.text_input("Nombre", key="new_in", label_visibility="collapsed", placeholder="Nueva entrada")
        with col2:
            if st.button("Añadir", use_container_width=True) and nueva:
                if nueva not in st.session_state.entradas:
                    st.session_state.entradas[nueva] = False
                    st.rerun()

    st.divider()
    st.markdown("### ⚡ Añadir Rung")
    
    # Editor para crear un nuevo escalón (Rung)
    with st.expander("Editor de Rung", expanded=len(st.session_state.rungs) == 0):
        num = st.number_input("Contactos en serie", 1, 5, 1, key="num_c")
        contactos = []
        for i in range(int(num)):
            c1, c2 = st.columns([3, 1])
            with c1:
                nom = st.text_input(f"Contacto {i+1}", value="Start", key=f"n_{i}")
            with c2:
                tipo = st.selectbox("Tipo", ["NA", "NC"], key=f"t_{i}")
            contactos.append(Contacto(nom, tipo))
        bob = st.text_input("Bobina (salida)", value="Lamp", key="bob_name")
        
        if st.button("➕ Añadir Rung", use_container_width=True, type="primary"):
            st.session_state.rungs.append(Rung(contactos, Bobina(bob)))
            st.rerun()

    st.divider()
    st.markdown("### 📋 Programa Ladder")
    if not st.session_state.rungs:
        st.info("Aún no hay rungs. Añade uno para empezar.")
        return

    # Evaluamos la lógica de todos los rungs con las entradas actuales
    for r in st.session_state.rungs:
        r.evaluar(st.session_state.entradas)

    # Mostramos los rungs visualmente
    for i, rung in enumerate(st.session_state.rungs):
        with st.container(border=True):
            h1, h2 = st.columns([5, 1])
            with h1:
                st.markdown(f"**Rung {i+1}**")
            with h2:
                if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                    st.session_state.rungs.pop(i)
                    st.rerun()
            
            # Dibujamos los contactos (🟢 si pasan energía, ⚪/🔴 si no)
            partes = []
            for c in rung.contactos:
                v = st.session_state.entradas.get(c.nombre, False)
                icon = ("🟢" if v else "⚪") if c.tipo == "NA" else ("🔴" if v else "🟢")
                partes.append(f"{icon} {c.nombre}")
            st.markdown(" — ".join(partes))
            
            # Mostramos el estado de la bobina
            estado = "🟡 **ON**" if rung.bobina.estado else "⚫ OFF"
            st.markdown(f"➡️ **{rung.bobina.nombre}**: {estado}")

    st.divider()
    # Sección para guardar el proyecto en la nube
    with st.expander("💾 Guardar / Actualizar programa"):
        default_name = st.session_state.current_project_name or ""
        nombre = st.text_input("Nombre del proyecto", value=default_name, key="save_name")
        if st.button("💾 Guardar en Supabase", use_container_width=True, type="primary"):
            if nombre:
                save_project(nombre)
            else:
                st.warning("Ponle un nombre al proyecto.")


# =====================================================================
# 8. INTERFAZ DE PROYECTOS GUARDADOS
# =====================================================================
def show_projects():
    st.markdown("### 📁 Mis Proyectos")
    proyectos = list_projects()
    if not proyectos:
        st.info("Aún no tienes proyectos guardados.")
        return
    
    for p in proyectos:
        with st.container(border=True):
            st.markdown(f"**{p['name']}**")
            st.caption(f"Actualizado: {p['updated_at'][:10]}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📂 Cargar", key=f"ld_{p['id']}", use_container_width=True):
                    load_project(p["id"])
            with c2:
                if st.button("🗑️", key=f"dl_{p['id']}", use_container_width=True):
                    delete_project(p["id"])


# =====================================================================
# 9. INTERFAZ DE PROGRESO (Gamificación)
# =====================================================================
def show_progress():
    st.markdown("### 🏆 Tu Progreso")
    try:
        # Busca los puntos XP y nivel del usuario
        res = supabase.table("profiles").select("xp,level").eq("id", st.session_state.user.id).single().execute()
        prof = res.data or {}
    except Exception:
        prof = {}
    
    c1, c2 = st.columns(2)
    c1.metric("XP", prof.get("xp", 0))
    c2.metric("Nivel", prof.get("level", 1))
    st.info("🎯 Los retos con XP llegan en la siguiente fase.")


# =====================================================================
# 10. PANTALLA PRINCIPAL (Cuando el usuario ya inició sesión)
# =====================================================================
def show_main():
    st.markdown("# 🔌 PLC Academy")
    
    # Determinamos el texto del rol según el JWT
    rol_texto = "👑 Administrador" if st.session_state.user_role == "admin" else "🎓 Estudiante"
    st.caption(f"👤 {st.session_state.user.email} | {rol_texto}")
    
    # Botón para salir
    if st.button("Cerrar sesión", use_container_width=True):
        supabase.auth.sign_out()
        for k in list(st.session_state.keys()):
            if k != "sb": del st.session_state[k]
        st.rerun()
        
    st.divider()
    
    # Pestañas de la app
    tabs = ["🎛️ Simulador", "📁 Proyectos", "🏆 Progreso"]
    tab_objects = st.tabs(tabs)
    
    with tab_objects[0]: show_simulator()
    with tab_objects[1]: show_projects()
    with tab_objects[2]: show_progress()


# =====================================================================
# 11. ENRUTADOR PRINCIPAL (Decide qué mostrar)
# =====================================================================
if st.session_state.user is None:
    show_login()
else:
    show_main()
