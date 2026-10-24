import streamlit as st
from supabase import create_client
from datetime import datetime, timezone

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
        return True, "Guardado exitoso"
    except Exception as e:
        return False, f"Error al guardar en BD: {e}"

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

# --- ESTAS SON LAS FUNCIONES QUE FALTABAN ---
def obtener_tiempo_inicio(user_id):
    try:
        supabase = conectar_supabase()
        res = supabase.table("profiles").select("session_start_time").eq("id", user_id).execute()
        if res.data and res.data[0]["session_start_time"]:
            fecha_str = res.data[0]["session_start_time"]
            return datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
        return None
    except Exception:
        return None

def guardar_tiempo_inicio(user_id):
    try:
        supabase = conectar_supabase()
        ahora = datetime.now(timezone.utc).isoformat()
        supabase.table("profiles").update({"session_start_time": ahora}).eq("id", user_id).execute()
    except:
        pass
