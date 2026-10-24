import streamlit as st

def dibujar_ladder(rungs, entradas, variables_numericas):
    for rung in rungs:
        rung.evaluar(entradas, variables_numericas)
        html = "<div style='border-left: 4px solid #00ff00; border-right: 4px solid #00ff00; padding: 20px; margin: 10px 0; background-color: #1a1c24; display: flex; align-items: center; overflow-x: auto;'>"
        
        for c in rung.contactos:
            if c.tipo == "P": simbolo, color = "|P|", "#00ff00" if getattr(c, 'anterior', False) else "#555"
            elif c.tipo == "N": simbolo, color = "|N|", "#00ff00" if getattr(c, 'anterior', False) else "#555"
            else:
                v = entradas.get(c.nombre, False)
                activo = v if c.tipo == "NA" else not v
                color = "#00ff00" if activo else "#555"
                simbolo = "| |" if c.tipo == "NA" else "|/|"
            
            html += f"<span style='border: 2px solid {color}; padding: 8px 15px; margin: 0 5px; color: {color}; font-weight: bold; font-family: monospace; border-radius: 5px;'>{c.nombre} {simbolo}</span>"
            html += "<span style='color: #555;'>———</span>"
            
        elem = rung.elemento
        color_elem = "#00ff00" if getattr(elem, 'estado', False) else "#555"
        bg_elem = "rgba(0, 255, 0, 0.2)" if getattr(elem, 'estado', False) else "transparent"
        
        if elem.__class__.__name__ == "Bobina":
            txt = f"( {elem.nombre} )" if elem.tipo=="Normal" else (f"( S {elem.nombre} )" if elem.tipo=="Set" else f"( R {elem.nombre} )")
            html += f"<span style='border: 2px solid {color_elem}; background-color: {bg_elem}; border-radius: 20px; padding: 8px 20px; margin-left: 10px; color: {color_elem}; font-weight: bold; font-family: monospace;'>{txt}</span>"
        elif elem.__class__.__name__ == "Temporizador":
            html += f"<span style='border: 2px solid {color_elem}; background-color: {bg_elem}; padding: 8px 15px; margin-left: 10px; color: {color_elem}; font-weight: bold; font-family: monospace;'>[ {elem.tipo} {elem.nombre} = {elem.tiempo}s ]</span>"
        elif elem.__class__.__name__ == "Contador":
            html += f"<span style='border: 2px solid {color_elem}; background-color: {bg_elem}; padding: 8px 15px; margin-left: 10px; color: {color_elem}; font-weight: bold; font-family: monospace;'>[ {elem.tipo} {elem.nombre} : {elem.preset} ]</span>"
        elif elem.__class__.__name__ == "Comparador":
            html += f"<span style='border: 2px solid {color_elem}; background-color: {bg_elem}; padding: 8px 15px; margin-left: 10px; color: {color_elem}; font-weight: bold; font-family: monospace;'>[ {elem.nombre} {elem.operador} {elem.valor} ]</span>"

        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

def dibujar_gemelo_digital(rungs):
    st.markdown("### Panel de Planta (Gemelo Digital)")
    col1, col2 = st.columns(2)
    lampara = any(r.elemento.nombre == "Lamp" and getattr(r.elemento, 'estado', False) for r in rungs if r.elemento.__class__.__name__ == "Bobina")
    motor = any(r.elemento.nombre == "Motor" and getattr(r.elemento, 'estado', False) for r in rungs if r.elemento.__class__.__name__ == "Bobina")
    
    with col1:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Lámpara</h3>", unsafe_allow_html=True)
            if lampara:
                st.markdown("<h1 style='text-align: center; font-size: 80px;'>💡</h1>", unsafe_allow_html=True)
                st.success("ENCENDIDA")
            else:
                st.markdown("<h1 style='text-align: center; font-size: 80px; filter: grayscale(100%); opacity: 0.3;'>💡</h1>", unsafe_allow_html=True)
                st.info("APAGADA")
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Motor</h3>", unsafe_allow_html=True)
            if motor:
                st.markdown("<h1 style='text-align: center; font-size: 80px;'>⚙️</h1>", unsafe_allow_html=True)
                st.success("GIRANDO")
            else:
                st.markdown("<h1 style='text-align: center; font-size: 80px; filter: grayscale(100%); opacity: 0.3;'>⚙️</h1>", unsafe_allow_html=True)
                st.info("DETENIDO")
