import streamlit as st
import time
from datetime import datetime
from supabase import create_client

# =====================================================================
# 1. CONFIGURACIÓN
# =====================================================================
st.set_page_config(page_title="PLC Academy", page_icon="⚙️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0e1117; color: white; }
    .ladder-rail { border-left: 3px solid #4a4a4a; border-right: 3px solid #4a4a4a; padding: 15px; margin: 15px 0; background-color: #1e1e1e; border-radius: 8px;}
    .contact-box { display: inline-block; border: 2px solid #555; padding: 5px 15px; margin: 0 5px; border-radius: 4px; font-weight: bold; font-family: monospace; font-size: 16px;}
    .contact-active { border-color: #00ff00; color: #00ff00; box-shadow: 0 0 10px #00ff00; }
    .coil-box { display: inline-block; border: 2px solid #555; padding: 5px 20px; border-radius: 20px; font-weight: bold; font-family: monospace; font-size: 16px;}
    .coil-active { border-color: #00ff00; background-color: rgba(0, 255, 0, 0.1); color: #00ff00; box-shadow: 0 0 15px #00ff00; }
    .timer-box { background-color: #262730; padding: 10px; border-radius: 8px; text-align: center; font-size: 18px; font-weight: bold; border: 1px solid #555;}
    .theory-box { background-color: #1e1e1e; padding: 20px; border-radius: 8px; border-left: 5px solid #ff4b4b; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. SUPABASE
# =====================================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
if "sb" not in st.session_state:
    st.session_state.sb = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase = st.session_state.sb

# =====================================================================
# 3. MODELO LADDER
# =====================================================================
class Contacto:
    def __init__(self, nombre, tipo="NA"):
        self.nombre = nombre; self.tipo = tipo
    def evaluar(self, entradas):
        v = entradas.get(self.nombre, False)
        return v if self.tipo == "NA" else not v
    def to_dict(self): return {"nombre": self.nombre, "tipo": self.tipo}
    @classmethod
    def from_dict(cls, d): return cls(d["nombre"], d["tipo"])

class Bobina:
    def __init__(self, nombre): self.nombre = nombre; self.estado = False
    def to_dict(self): return {"nombre": self.nombre}
    @classmethod
    def from_dict(cls, d): return cls(d["nombre"])

class Rung:
    def __init__(self, contactos, bobina):
        self.contactos = contactos; self.bobina = bobina
    def evaluar(self, entradas):
        for c in self.contactos:
            if not c.evaluar(entradas):
                self.bobina.estado = False; return
        self.bobina.estado = True
    def to_dict(self): return {"contactos": [c.to_dict() for c in self.contactos], "bobina": self.bobina.to_dict()}
    @classmethod
    def from_dict(cls, d): return cls([Contacto.from_dict(c) for c in d["contactos"]], Bobina.from_dict(d["bobina"]))

# =====================================================================
# 4. ESTADO Y TEMPORIZADOR (Con reloj real)
# =====================================================================
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.user_role = "student"
    st.session_state.rungs = []
    st.session_state.entradas = {"Start": False, "Stop": False}
    st.session_state.start_time = time.time() # Guarda el momento en que entró
    st.session_state.mission_active = False
    st.session_state.mission_success = False

# =====================================================================
# 5. LOGIN
# =====================================================================
def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("⚙️ PLC Academy")
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Entrar", use_container_width=True, type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user
                    rol_query = supabase.table("user_roles").select("role").eq("user_id", res.user.id).execute()
                    st.session_state.user_role = rol_query.data[0]["role"] if rol_query.data else "student"
                    st.session_state.start_time = time.time() # Reinicia el reloj al entrar
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# =====================================================================
# 6. SIMULADOR
# =====================================================================
def show_simulator():
    # Calcular tiempo transcurrido
    elapsed_seconds = time.time() - st.session_state.start_time
    elapsed_minutes = int(elapsed_seconds // 60)

    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("Entorno de Simulación")
    with col_t2:
        st.markdown(f"<div class='timer-box'>⏱️ Sesión: {elapsed_minutes} / 60 min</div>", unsafe_allow_html=True)
        
    st.divider()

    if elapsed_minutes >= 60:
        st.error("🎉 ¡Misión Cumplida por hoy! Has alcanzado los 60 minutos de estudio recomendados.")
        st.info("El cerebro necesita descansar para consolidar lo aprendido. Cierra la app y vuelve mañana.")
        if st.button("Reiniciar Temporizador (Para probar)"):
            st.session_state.start_time = time.time()
            st.rerun()
        return

    # Panel de Entradas
    st.write("**Panel de Entradas (I/O)**")
    cols = st.columns(len(st.session_state.entradas))
    for i, nombre in enumerate(list(st.session_state.entradas.keys())):
        with cols[i]:
            st.session_state.entradas[nombre] = st.toggle(nombre, value=st.session_state.entradas[nombre], key=f"tog_{nombre}")

    st.divider()

    # Evaluar lógica y dibujar
    for r in st.session_state.rungs:
        r.evaluar(st.session_state.entradas)

    # Verificar Misión
    if st.session_state.mission_active and not st.session_state.mission_success:
        if len(st.session_state.rungs) == 2:
            bob = st.session_state.rungs[1].bobina.estado
            start = st.session_state.entradas.get("Start", False)
            if bob and not start:
                st.session_state.mission_success = True
                st.balloons()
                st.success("🏆 ¡MISIÓN COMPLETADA! Has dominado el Enclavamiento.")

    st.write("**Diagrama Ladder en Vivo**")
    if not st.session_state.rungs:
        st.info("Ve a la pestaña 'Academia' y selecciona un módulo.")
        return

    for i, rung in enumerate(st.session_state.rungs):
        with st.container():
            html_rung = "<div class='ladder-rail'>"
            html_rung += "<div style='display:flex; align-items:center;'>"
            
            for c in rung.contactos:
                v = st.session_state.entradas.get(c.nombre, False)
                activo = v if c.tipo == "NA" else not v
                simbolo = "—| |—" if activo else "—|/|—"
                color_class = "contact-active" if activo else ""
                html_rung += f"<span class='contact-box {color_class}'>{c.nombre} {simbolo}</span>"
            
            bob_activa = rung.bobina.estado
            color_bob = "coil-active" if bob_activa else ""
            html_rung += f"<span class='coil-box {color_bob}'> ( {rung.bobina.nombre} ) </span>"
            
            html_rung += "</div></div>"
            st.markdown(html_rung, unsafe_allow_html=True)

# =====================================================================
# 7. ACADEMIA (TEORÍA Y PRÁCTICA)
# =====================================================================
def show_academy():
    st.subheader("Plan de Estudios PLC")
    
    # Pestañas para separar Teoría de Práctica
    tab_teoria, tab_practica = st.tabs(["📖 Teoría (Fundamentos)", "🛠️ Práctica (Misiones)"])

    # --- PESTAÑA DE TEORÍA ---
    with tab_teoria:
        st.markdown("### Módulo 0: Introducción a la Automatización")
        
        with st.expander("1. ¿Qué es un PLC y para qué sirve?", expanded=True):
            st.markdown("""
            <div class='theory-box'>
            <b>PLC (Controlador Lógico Programable):</b> Es una computadora industrial robusta diseñada para controlar maquinaria en entornos hostiles (polvo, calor, vibraciones). 
            <br><br>
            Antes de los PLCs, las fábricas usaban miles de relés electromecánicos que se desgastaban y era imposible reprogramar. El PLC nació en 1968 (por Dick Morley, considerado el padre del PLC) para reemplazar esos relés con software.
            </div>
            """, unsafe_allow_html=True)
            
        with st.expander("2. El Estándar IEC 61131-3 y los Lenguajes"):
            st.markdown("""
            Para que todas las marcas hablaran el mismo idioma, se creó el estándar **IEC 61131-3**. Define 5 lenguajes:
            *   **Ladder (LD):** Gráfico, basado en esquemas eléctricos. (El que usamos aquí).
            *   **FBD (Function Block Diagram):** Gráfico, usa bloques lógicos interconectados.
            *   **ST (Structured Text):** Textual, similar a Pascal o C. Muy usado para matemáticas complejas.
            *   **IL (Instruction List):** Textual, tipo ensamblador (en desuso).
            *   **SFC (Sequential Function Chart):** Gráfico de estados, para procesos paso a paso.
            """)

        with st.expander("3. Grandes Marcas: Siemens, Allen-Bradley y ABB"):
            st.markdown("""
            *   **Siemens (Alemania):** El gigante europeo. Su software se llama **TIA Portal**. Usa Ladder y un lenguaje propio llamado **SCL** (Structured Control Language).
            *   **Allen-Bradley / Rockwell (EE. UU.):** El rey en América. Su software es **Studio 5000** (antes RSLogix). Su lenguaje textual se llama **ST**.
            *   **ABB (Suiza):** Muy fuerte en robótica y control de motores. Su software es **Automation Builder**.
            *   **Schneider Electric (Francia):** Su software es **EcoStruxure** (antes Unity Pro).
            """)

        with st.expander("4. ¿Cómo funciona el ciclo de Scan del PLC?"):
            st.markdown("""
            Un PLC no es como una PC normal; no ejecuta todo al mismo tiempo. Hace un ciclo repetitivo llamado **Scan Cycle**:
            1.  **Leer Entradas:** Mira qué sensores están encendidos.
            2.  **Ejecutar Programa:** Resuelve la lógica Ladder de arriba hacia abajo.
            3.  **Actualizar Salidas:** Enciende o apaga los motores/luces.
            4.  **Repetir:** Vuelve al paso 1 en milisegundos.
            """)

    # --- PESTAÑA DE PRÁCTICA ---
    with tab_practica:
        st.markdown("### Misiones Prácticas")
        st.write("Carga una misión y ve al simulador para resolverla.")
        
        misiones = {
            "Misión 1: Enclavamiento (Self-Holding)": {
                "desc": "Mantén la lámpara encendida después de soltar el pulsador.\n\n**Instrucciones:**\n1. Activa Start.\n2. Apaga Start.\n3. Si la lámpara sigue encendida, ¡lo lograste!\n4. Activa Stop para apagarla.",
                "rungs": [
                    Rung([Contacto("Start", "NA")], Bobina("Lamp")),
                    Rung([Contacto("Lamp", "NA"), Contacto("Stop", "NC")], Bobina("Lamp"))
                ],
                "entradas": {"Start": False, "Stop": False}
            },
            "Misión 2: Lógica AND (Seguridad)": {
                "desc": "La máquina solo enciende si el Operador presiona Start Y el Sensor de seguridad está activo.",
                "rungs": [
                    Rung([Contacto("Start", "NA"), Contacto("Sensor", "NA")], Bobina("Lamp"))
                ],
                "entradas": {"Start": False, "Sensor": False}
            }
        }

        for titulo, data in misiones.items():
            with st.container(border=True):
                st.markdown(f"#### {titulo}")
                st.write(data["desc"])
                if st.button(f"Cargar Misión", key=titulo, type="primary"):
                    st.session_state.rungs = data["rungs"]
                    st.session_state.entradas = data["entradas"]
                    st.session_state.mission_active = True
                    st.session_state.mission_success = False
                    st.success("Misión cargada. Ve a la pestaña 'Simulador Visual'.")
                    st.rerun()

# =====================================================================
# 8. MAIN
# =====================================================================
def show_main():
    col1, col2 = st.columns([8, 2])
    with col1:
        rol = "ADMINISTRADOR" if st.session_state.user_role == "admin" else "ESTUDIANTE"
        st.markdown(f"**Usuario:** {st.session_state.user.email} | **Rol:** `{rol}`")
    with col2:
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()
            
    st.divider()
    
    tab1, tab2 = st.tabs(["Simulador Visual", "Academia (Curso)"])
    with tab1: show_simulator()
    with tab2: show_academy()

if st.session_state.user is None:
    show_login()
else:
    show_main()
