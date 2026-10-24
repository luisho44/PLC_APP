class Contacto:
    def __init__(self, nombre, tipo="NA"):
        self.nombre = nombre; self.tipo = tipo
    def evaluar(self, entradas):
        v = entradas.get(self.nombre, False)
        return v if self.tipo == "NA" else not v

class Bobina:
    def __init__(self, nombre): 
        self.nombre = nombre; self.estado = False

class Rung:
    def __init__(self, contactos, bobina):
        self.contactos = contactos; self.bobina = bobina
    def evaluar(self, entradas):
        for c in self.contactos:
            if not c.evaluar(entradas):
                self.bobina.estado = False; return
        self.bobina.estado = True
