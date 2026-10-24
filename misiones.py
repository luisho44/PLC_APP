from logica_plc import Rung, Contacto, Bobina

def obtener_temario():
    return {
        1: {
            "titulo": "Contactos y Bobinas (Lógica Básica)",
            "prompt_ia": "Explica la diferencia entre un contacto Normalmente Abierto (NA) y uno Normalmente Cerrado (NC), y cómo se usa una bobina de salida.",
            "rungs": [Rung([Contacto("Start", "NA")], Bobina("Lamp"))],
            "entradas": {"Start": False}
        },
        2: {
            "titulo": "El Enclavamiento (Self-Holding)",
            "prompt_ia": "Explica el circuito de enclavamiento. Cómo mantener una bobina encendida después de soltar Start, usando el propio contacto del Motor en paralelo con Start, y un Stop en serie.",
            # Práctica corregida: Un solo Rung con el Stop en serie.
            "rungs": [
                Rung([Contacto("Start", "NA"), Contacto("Motor", "NA"), Contacto("Stop", "NC")], Bobina("Motor"))
            ],
            "entradas": {"Start": False, "Stop": False}
        },
        3: {
            "titulo": "Lógica Combinacional (AND)",
            "prompt_ia": "Explica cómo poner dos contactos en serie (Lógica AND) para seguridad de una máquina.",
            "rungs": [Rung([Contacto("Start", "NA"), Contacto("Sensor", "NA")], Bobina("Lamp"))],
            "entradas": {"Start": False, "Sensor": False}
        }
    }
