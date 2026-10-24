import streamlit as st
import os
import jwt
from supabase import create_client

# ============ CONFIG ============
st.set_page_config(
    page_title="PLC Academy",
    page_icon="🔌",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Leer credenciales de forma más segura
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")

# Si por alguna razón están vacías, mostramos un error más detallado
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Error de configuración: No se encontraron las credenciales.")
    st.info(f"¿La URL está vacía? {SUPABASE_URL == ''} | ¿La KEY está vacía? {SUPABASE_KEY == ''}")
    st.stop()

if "sb" not in st.session_state:
    st.session_state.sb = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase = st.session_state.sb

# ============ MODELO LADDER ============
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

# ============ ESTADO DE SESIÓN ============
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

# ============ AUTH ============
def show_login():
    st.markdown("# 🔌 PLC Academy")
    st.caption("Aprende Ladder Logic desde tu celular")
    st.divider()
    
    tab_login, tab_reg = st.tabs(["🔑 Iniciar sesión", "✨ Crear cuenta"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("📧 Email")
            pw = st.text_input("🔒 Contraseña", type="password")
            ok = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            if ok and email and pw:
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
                    st.error(f"❌ Error: {e}")

    with tab_reg:
        with st.form("reg_form"):
            email = st.text_input("📧 Email", key="r_email")
            pw = st.text_input("🔒 Contraseña (mín. 6 caract.)", type="password", key="r_pw")
            ok = st.form_submit_button("Crear cuenta", use_container_width=True, type="primary")
            if ok and email and pw:
                try:
                    supabase.auth.sign_up({"email": email, "password": pw})
                    st.success("✅ Cuenta creada. Ahora inicia sesión.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ============ PERSISTENCIA ============
def save_project(name):
    if not st.session_state.rungs:
        st.warning("No hay rungs para guardar.")
        return
    data = {"rungs": [r.to_dict() for r in st.session_state.rungs], "entradas": st.session_state.entradas}
    try:
        if st.session_state.current_project_id:
            supabase.table("projects").update({"name": name, "program_data": data}).eq("id", st.session_state.current_project_id).execute()
            st.success(f"💾 Proyecto '{name}' actualizado")
        else:
            res = supabase.table("projects").insert({"user_id": st.session_state.user.id, "name": name, "program_data": data}).execute()
            st.session_state.current_project_id = res.data[0]["id"]
            st.success(f"💾 Proyecto '{name}' guardado")
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
        st.success(f"📂 '{p['name']}' cargado")
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

def delete_project(pid):
    try:
        supabase.table("projects").delete().eq("id", pid).execute()
        if st.session_state.current_project_id == pid:
            st.session_state.current_project_id = None
            st.session_state.current_project_name = None
        st.success("🗑️ Proyecto eliminado")
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# ============ UI SIMULADOR ============
def show_simulator():
    st.markdown("### 🎛️ Panel de Entradas")
    for nombre in list(st.session_state.entradas.keys()):
        st.session_state.entradas[nombre] = st.toggle(f"**{nombre}**", value=st.session_state.entradas[nombre], key=f"tog_{nombre}")

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

    for r in st.session_state.rungs:
        r.evaluar(st.session_state.entradas)

    for i, rung in enumerate(st.session_state.rungs):
        with st.container(border=True):
            h1, h2 = st.columns([5, 1])
            with h1:
                st.markdown(f"**Rung {i+1}**")
            with h2:
                if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                    st.session_state.rungs.pop(i)
                    st.rerun()
            partes = []
            for c in rung.contactos:
                v = st.session_state.entradas.get(c.nombre, False)
                icon = ("🟢" if v else "⚪") if c.tipo == "NA" else ("🔴" if v else "🟢")
                partes.append(f"{icon} {c.nombre}")
            st.markdown(" — ".join(partes))
            estado = "🟡 **ON**" if rung.bobina.estado else "⚫ OFF"
            st.markdown(f"➡️ **{rung.bobina.nombre}**: {estado}")

    st.divider()
    with st.expander("💾 Guardar / Actualizar programa"):
        default_name = st.session_state.current_project_name or ""
        nombre = st.text_input("Nombre del proyecto", value=default_name, key="save_name")
        if st.button("💾 Guardar en Supabase", use_container_width=True, type="primary"):
            if nombre:
                save_project(nombre)
            else:
                st.warning("Ponle un nombre al proyecto.")

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

def show_progress():
    st.markdown("### 🏆 Tu Progreso")
    try:
        res = supabase.table("profiles").select("xp,level").eq("id", st.session_state.user.id).single().execute()
        prof = res.data or {}
    except Exception:
        prof = {}
    c1, c2 = st.columns(2)
    c1.metric("XP", prof.get("xp", 0))
    c2.metric("Nivel", prof.get("level", 1))
    st.info("🎯 Los retos con XP llegan en la siguiente fase.")

# ============ APP PRINCIPAL ============
def show_main():
    st.markdown("# 🔌 PLC Academy")
    
    rol_texto = "👑 Administrador" if st.session_state.user_role == "admin" else "🎓 Estudiante"
    st.caption(f"👤 {st.session_state.user.email} | {rol_texto}")
    
    if st.button("Cerrar sesión", use_container_width=True):
        supabase.auth.sign_out()
        for k in list(st.session_state.keys()):
            if k != "sb": del st.session_state[k]
        st.rerun()
        
    st.divider()
    
    tabs = ["🎛️ Simulador", "📁 Proyectos", "🏆 Progreso"]
    tab_objects = st.tabs(tabs)
    
    with tab_objects[0]: show_simulator()
    with tab_objects[1]: show_projects()
    with tab_objects[2]: show_progress()

# ============ ROUTER ============
if st.session_state.user is None:
    show_login()
else:
    show_main()
