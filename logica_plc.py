class Contacto:
    def __init__(self, nombre, tipo="NA"):
        self.nombre = nombre; self.tipo = tipo
    def evaluar(self, entradas):
        v = entradas.get(self.nombre, False)
        if self.tipo == "NA": return v
        if self.tipo == "NC": return not v
        if self.tipo == "P": # Flanco de subida
            anterior = getattr(self, 'anterior', False)
            self.anterior = v
            return v and not anterior
        if self.tipo == "N": # Flanco de bajada
            anterior = getattr(self, 'anterior', False)
            self.anterior = v
            return not v and anterior
        return False

class Bobina:
    def __init__(self, nombre, tipo="Normal"): 
        self.nombre = nombre; self.tipo = tipo
        self.estado = False

class Temporizador:
    def __init__(self, nombre, tipo="TON", tiempo=3):
        self.nombre = nombre; self.tipo = tipo
        self.tiempo = tiempo
        self.estado = False

class Contador:
    def __init__(self, nombre, tipo="CTU", preset=5):
        self.nombre = nombre; self.tipo = tipo
        self.preset = preset
        self.conteo = 0
        self.estado = False

class Comparador:
    def __init__(self, nombre, operador=">", valor=50):
        self.nombre = nombre; self.operador = operador; self.valor = valor
        self.estado = False

class Rung:
    def __init__(self, contactos, elemento):
        self.contactos = contactos; self.elemento = elemento
        
    def evaluar(self, entradas, variables_numericas=None):
        pasa_energia = True
        for c in self.contactos:
            if not c.evaluar(entradas):
                pasa_energia = False
                break
                
        if isinstance(self.elemento, Bobina):
            if pasa_energia:
                if self.elemento.tipo == "Normal": self.elemento.estado = True
                elif self.elemento.tipo == "Set": self.elemento.estado = True
            else:
                if self.elemento.tipo == "Normal": self.elemento.estado = False
                
        elif isinstance(self.elemento, Temporizador) or isinstance(self.elemento, Contador):
            self.elemento.estado = pasa_energia
            
        elif isinstance(self.elemento, Comparador):
            val_actual = variables_numericas.get(self.elemento.nombre, 0) if variables_numericas else 0
            if self.elemento.operador == ">": self.elemento.estado = val_actual > self.elemento.valor
            elif self.elemento.operador == "<": self.elemento.estado = val_actual < self.elemento.valor
            elif self.elemento.operador == "==": self.elemento.estado = val_actual == self.elemento.valor
