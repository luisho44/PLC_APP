import streamlit as st
from supabase import create_client

def conectar_supabase():
    URL = st.secrets.get("SUPABASE_URL", "")
    KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(URL, KEY)
    return st.session_state.sb

def agente_guardar_historial(supabase, user_id, minutos, mision):
    try:
        supabase.table("progreso_historico").insert({
            "user_id": user_id,
            "minutos_estudiados": minutos,
            "mision_completada": mision
        }).execute()
    except: pass

# --- FUNCIONES EXCLUSIVAS DEL ADMINISTRADOR ---
def admin_ver_todos_los_usuarios(supabase):
    try:
        res = supabase.table("profiles").select("username, xp, level").execute()
        return res.data
    except: return []

def admin_ver_todo_el_progreso(supabase):
    try:
        res = supabase.table("progreso_historico").select("*").order("fecha", desc=True).execute()
        return res.data
    except: return []
