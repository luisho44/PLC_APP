import streamlit as st
from logica_plc import Rung, Contacto, Bobina

def dibujar_ladder(rungs, entradas):
    for rung in rungs:
        rung.evaluar(entradas)
        html = "<div style='border-left: 3px solid #555; border-right: 3px solid #555; padding: 15px; margin: 10px 0; background-color: #1e1e1e;'>"
        for c in rung.contactos:
            v = entradas.get(c.nombre, False)
            activo = v if c.tipo == "NA" else not v
            color = "#00ff00" if activo else "#555"
            html += f"<span style='border: 2px solid {color}; padding: 5px; margin: 0 5px; color: {color};'>{c.nombre}</span>"
        
        color_bob = "#00ff00" if rung.bobina.estado else "#555"
        html += f"<span style='border: 2px solid {color_bob}; border-radius: 20px; padding: 5px 15px; margin-left: 20px; color: {color_bob};'>( {rung.bobina.nombre} )</span>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
