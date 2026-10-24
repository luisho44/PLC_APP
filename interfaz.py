import streamlit as st

def dibujar_ladder(rungs, entradas):
    for rung in rungs:
        rung.evaluar(entradas)
        html = "<div style='border-left: 4px solid #00ff00; border-right: 4px solid #00ff00; padding: 20px; margin: 10px 0; background-color: #1a1c24; display: flex; align-items: center;'>"
        
        for c in rung.contactos:
            v = entradas.get(c.nombre, False)
            activo = v if c.tipo == "NA" else not v
            color = "#00ff00" if activo else "#555"
            simbolo = "| |" if activo else "|/|"
            html += f"<span style='border: 2px solid {color}; padding: 8px 15px; margin: 0 5px; color: {color}; font-weight: bold; font-family: monospace; border-radius: 5px;'>{c.nombre} {simbolo}</span>"
            html += "<span style='color: #555;'>———</span>"
            
        color_bob = "#00ff00" if rung.bobina.estado else "#555"
        bg_bob = "rgba(0, 255, 0, 0.2)" if rung.bobina.estado else "transparent"
        html += f"<span style='border: 2px solid {color_bob}; background-color: {bg_bob}; border-radius: 20px; padding: 8px 20px; margin-left: 10px; color: {color_bob}; font-weight: bold; font-family: monospace;'> ( {rung.bobina.nombre} ) </span>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

def dibujar_gemelo_digital(rungs):
    st.markdown("### Panel de Planta (Gemelo Digital)")
    st.write("Así se vería la maquinaria real si tu código Ladder se ejecutara en un PLC físico.")
    
    col1, col2 = st.columns(2)
    
    # Verificamos estados de las bobinas
    lampara_encendida = any(r.bobina.nombre == "Lamp" and r.bobina.estado for r in rungs)
    motor_encendido = any(r.bobina.nombre == "Motor" and r.bobina.estado for r in rungs)
    
    with col1:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Lámpara de Planta</h3>", unsafe_allow_html=True)
            if lampara_encendida:
                st.markdown("<h1 style='text-align: center; font-size: 80px;'>💡</h1>", unsafe_allow_html=True)
                st.success("ESTADO: ENCENDIDA (220V)")
            else:
                st.markdown("<h1 style='text-align: center; font-size: 80px; filter: grayscale(100%); opacity: 0.3;'>💡</h1>", unsafe_allow_html=True)
                st.info("ESTADO: APAGADA")

    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Motor de Inducción</h3>", unsafe_allow_html=True)
            if motor_encendido:
                st.markdown("<h1 style='text-align: center; font-size: 80px; animation: spin 2s linear infinite;'>⚙️</h1>", unsafe_allow_html=True)
                st.success("ESTADO: GIRANDO (1750 RPM)")
            else:
                st.markdown("<h1 style='text-align: center; font-size: 80px; filter: grayscale(100%); opacity: 0.3;'>⚙️</h1>", unsafe_allow_html=True)
                st.info("ESTADO: DETENIDO")
