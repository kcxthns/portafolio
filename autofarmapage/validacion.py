from itertools import cycle 

class Validador:
    
    def validarRut(self, rut, dv):
        suma = 0
        multiplicador = 2
        
        rutRevertido = map(int, reversed(str(rut)))
        factores = cycle(range(2,8))
        suma = sum(d*f for d, f in zip(rutRevertido, factores))
        resto = (-suma)%11

        if str(resto) == dv:
            return True
        elif dv.upper() == "K" and resto == 10:
            return True
        else:
            return False