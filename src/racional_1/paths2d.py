from pysvg.structure import *
from pysvg.builders import *

def obtienePath(n, m, d):
    digitos = []
    resto = m
    for _ in range(d):
        resto *= 4
        digito = 0
        while resto > n:
            resto -= n
            digito += 1
        digitos.append(digito)
    return digitos

class Matriz(object):
    def __init__(self, n, d):
        self.d = d
        self.n = n
        self.total = 0
        self.max = 0
        self.matriz = [[0 for x in range(2*d+1)] for x in range(2*d+1)]
        print len(self.matriz[0])
        
    def anadePath(self, path):
        x = 0
        y = 0
        for digito in path:
            if digito == 0:
                x += 1
            elif digito == 1:
                x -= 1
            elif digito == 2:
                y += 1
            else:
                y -= 1
        self.matriz[x+self.d][y+self.d] += 1
        num = self.matriz[x+self.d][y+self.d]
        if num > self.max:
            self.max = num
        self.total += 1    

    def calcula(self):
        for m in xrange(self.n):
            path = obtienePath(self.n, m, self.d)
            if m % 1000 == 0:
                print m
            self.anadePath(path)
        
    def dibuja(self):
        s=svg(height="100%", width="100%")
        s.set_viewBox("0 0 1000 1000")
        oh=ShapeBuilder()
        radio = 1000.0/(4*self.d)
        rmin = 5
        for x in range(2*self.d+1):
            for y in range(2*self.d+1):
                per = self.matriz[x][y]/float(self.max)
                px = x * 2.0 * radio
                py = y * 2.0 * radio
                if per > 0.0:
                    r = radio*per + rmin*(1-per)
                    c = oh.createCircle(px, py, r, fill='#000', stroke='none')
                else:
                    c = oh.createCircle(px, py, 5, fill='#F00', stroke='none')
                s.addElement(c)
                    
        s.save('paths/paths_%02d_%08d.svg'%(self.d, self.n))

def main():
    matriz = Matriz(16777215, 12)
    matriz.calcula()
    matriz.dibuja()
        
if __name__ == '__main__': 
    main()
