import streamlit as st
from supabase import create_client

def conectar_supabase():
    URL = st.secrets.get("SUPABASE_URL", "")
    KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(URL, KEY)
    return st.session_state.sb

def agente_guardar_historial(user_id, minutos, mision):
    try:
        supabase = conectar_supabase()
        supabase.table("progreso_historico").insert({
            "user_id": user_id, "minutos_estudiados": minutos, "mision_completada": mision
        }).execute()
    except Exception as e:
        st.error(f"Error guardando: {e}")

def obtener_misiones_completadas(user_id):
    try:
        supabase = conectar_supabase()
        res = supabase.table("progreso_historico").select("mision_completada").eq("user_id", user_id).execute()
        return [item["mision_completada"] for item in res.data]
    except:
        return []

def admin_ver_todos_los_usuarios():
    try:
        supabase = conectar_supabase()
        return supabase.table("profiles").select("id, username, xp, level").execute().data
    except:
        return []

def admin_ver_todo_el_progreso():
    try:
        supabase = conectar_supabase()
        return supabase.table("progreso_historico").select("*").order("fecha", desc=True).execute().data
    except:
        return []
