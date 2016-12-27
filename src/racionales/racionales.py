from math import pow

c = 0.5

class Racional():
    def __init__(self, m, n):
        self.m = m
        self.n = n
        
    def secuencia(self, d):
        base = int(pow(2, d))
        digitos = []
        restos = []
        resto = self.m
        digito = int(resto*base/self.n)
        while True:
            digitos.append(digito)
            restos.append(resto)
            resto = (resto*base)%self.n
            digito = int(resto*base/self.n)
            if resto == self.m:
                break
        return (digitos, restos)
    
    def camino(self, d):
        (digitos, _) = self.secuencia(d)
        cam = ''
        for d in digitos:
            cam += str(d)
        return cam
        
    def periodo(self, d):
        (digitos, _) = self.secuencia(d)
        return len(digitos)
    
    def posicion(self, t, d):
        (digitos, _) = self.secuencia(d)
        periodo = len(digitos)
        x = 0.0
        y = 0.0
        z = 0.0
        for i in range(t):
            digito = digitos[i%periodo]
            x +=     -(digito%2)    + c
            y += -(int(digito/2)%2) + c
            z += -(int(digito/4)%2) + c
        if   d == 1: return x 
        elif d == 2: return (x, y)
        elif d == 3: return (x, y, z)

