

class Path:
    def __init__(self, n, m, d):
        self.n = n
        self.m = m
        self.d = d
        self.digitos = []
        self.calcula()
        self.velocidades = []
        
    def calcula(self):
        resto = self.m
        for i in range(self.d):
            resto *= 2
            digito = 0
            while resto > self.n:
                resto -= self.n
                digito += 1
            self.digitos.append(digito)
    
    def calculaVelocidades(self, tiempo):
        x = 0.0
        v = 0.0
        self.velocidades.append(v)
        for t in range(1, tiempo+1):
            digito = self.digitos[t%self.d]
            if digito == 0:
                x += 1
            else:
                x -= 1
            v = x/float(t)
            self.velocidades.append(v)
    
    def obtieneVelocidad(self, t):
        return self.velocidades[t]
        
        
class Paths:
    def __init__(self, n, d, t):
        self.n = n
        self.d = d
        self.t = t
        self.paths = []
        
    def anadePath(self, m):
        path = Path(self.n, m, self.d)
        path.calculaVelocidades(self.t)
        self.paths.append(path)
        
    def vuelca(self, nombre):
        fp = open(nombre, 'wt')
        for t in range(self.t):
            salida = ''
            for path in self.paths:
                salida += '%5.4f;'%path.obtieneVelocidad(t)
            fp.write(salida+'\n')
        fp.close()
        
 
def main():
    paths = Paths(63, 6, 100)
    m = 3
    for i in range(6):
        paths.anadePath(m)
        m *= 2
        while m > 63:
            m -= 63
    paths.vuelca('velocidades/vel_%06d.txt'%paths.n)

if __name__ == '__main__': 
    main()

            
        
        
        
        