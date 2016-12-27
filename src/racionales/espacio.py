from copy import deepcopy
from racionales import Racional, c
from utils import divisores

class Espacio():
    def __init__(self, d, T):
        self.d = d
        self.T = T
        self.inicia()
        
    def inicia(self):
        self.esp = [0 for _ in range(self.T+1)]
        for _ in range(self.d-1):
            self.esp = [deepcopy(self.esp) for _ in range(self.T+1)]
            
    def anadeRacional(self, m, n):
        r = Racional(m, n)
        if self.d == 1:
            x = r.posicion(self.T, self.d)
            nx = int(x + c*self.T)
            self.esp[nx] += 1
        elif self.d == 2:
            x, y = r.posicion(self.T, self.d)
            nx = int(x + c*self.T)
            ny = int(y + c*self.T)
            self.esp[nx][ny] += 1
        elif self.d == 3:
            x, y, z = r.posicion(self.T, self.d)
            nx = int(x + c*self.T)
            ny = int(y + c*self.T)
            nz = int(z + c*self.T)
            self.esp[nx][ny][nz] += 1
            
    def anadeConjuntoRacional(self, n):
        for m in range(n):
            self.anadeRacional(m, n)
        if self.d == 1:
            self.esp[0] = 1
        elif self.d == 2:
            self.esp[0][0] = 1
        else:
            self.esp[0][0][0] = 1
        
  
    def imprime(self):
        if self.d == 1:
            output = ''
            for nx in range(self.T+1):
                t = self.esp[nx]
                output += '%d;'%t if t else ';'
        if self.d == 2:
            for ny in range(self.T+1):
                output = ''
                for nx in range(self.T+1):
                    t = self.esp[nx][ny]
                    output += '%d;'%t if t else ';'
                output += '\n'
        if self.d == 3:
            for nz in range(self.T+1):
                for ny in range(self.T+1):
                    output = ''
                    for nx in range(self.T+1):
                        t = self.esp[nx][ny][nz]
                        output += '%d;'%t if t else ';'
                    output += '\n'
                output += '\n' 
        return output

esp = Espacio(1, 12)
divs = divisores(int(pow(2, 12)-1))
with open('histograma_1d_2e12.csv', 'wt') as fp:
    for div in divs:
        esp.inicia()
        esp.anadeConjuntoRacional(div)
        linea = '%d;'%div + esp.imprime()
        fp.write(linea+'\n')
        print linea
