from logica_plc import Rung, Contacto, Bobina, Temporizador, Contador, Comparador

def obtener_temario():
    return {
        1: {
            "titulo": "Contactos y Bobinas",
            "prompt_ia": "Explica contactos NA, NC y bobinas de salida.",
            "rungs": [Rung([Contacto("Start", "NA")], Bobina("Lamp"))],
            "entradas": {"Start": False}
        },
        2: {
            "titulo": "Enclavamiento",
            "prompt_ia": "Explica el circuito de retención con Stop NC.",
            "rungs": [
                Rung([Contacto("Start", "NA")], Bobina("Motor")),
                Rung([Contacto("Motor", "NA"), Contacto("Stop", "NC")], Bobina("Motor"))
            ],
            "entradas": {"Start": False, "Stop": False}
        },
        3: {
            "titulo": "Flanco de Subida (P)",
            "prompt_ia": "Explica qué es un flanco de subida (Positive Edge). Se activa solo un instante al presionar.",
            "rungs": [Rung([Contacto("Start", "P")], Bobina("Lamp"))],
            "entradas": {"Start": False}
        },
        4: {
            "titulo": "Temporizador TON",
            "prompt_ia": "Explica el temporizador TON (Timer On Delay).",
            "rungs": [Rung([Contacto("Start", "NA")], Temporizador("Motor", "TON", 5))],
            "entradas": {"Start": False}
        },
        5: {
            "titulo": "Comparador (>)",
            "prompt_ia": "Explica cómo un PLC usa comparadores para tomar decisiones basadas en temperatura o presión.",
            "rungs": [Rung([Contacto("Start", "NA")], Comparador("Temperatura", ">", 50))],
            "entradas": {"Start": False}
        }
    }
