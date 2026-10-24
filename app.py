import streamlit as st
import pandas as pd
import time
import google.generativeai as genai
from datetime import datetime, timezone
from base_datos import (
    conectar_supabase, agente_guardar_historial, obtener_misiones_completadas, 
    admin_ver_todos_los_usuarios, admin_ver_todo_el_progreso,
    obtener_tiempo_inicio, guardar_tiempo_inicio
)
from logica_plc import Rung, Contacto, Bobina
from interfaz import dibujar_ladder, dibujar_gemelo_digital
from misiones import obtener_temario
