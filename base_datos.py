import streamlit as st
from supabase import create_client

def conectar_supabase():
    URL = st.secrets.get("SUPABASE_URL", "")
    KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(URL, KEY)
    return st.session_state.sb

def agente_guardar_historial(supabase, user_id, minutos, mision_completada):
    # El agente guarda el avance en la nube
    try:
        supabase.table("progreso_historico").insert({
            "user_id": user_id,
            "minutos_estudiados": minutos,
            "mision_completada": mision_completada
        }).execute()
    except Exception as e:
        print("Error guardando historial:", e)

def agente_obtener_historial(supabase, user_id):
    # El agente consulta qué has hecho
    try:
        res = supabase.table("progreso_historico").select("*").eq("user_id", user_id).execute()
        return res.data
    except:
        return []
