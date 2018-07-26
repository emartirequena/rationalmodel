from pysvg.structure import *
from pysvg.builders import *

from copy import deepcopy
from racionales import Racional, c
from utils import divisors


class Espacio():
    def __init__(self, d, T):
        self.d = d
        self.T = T
        self.inicia()
        self.max = 0

    def inicia(self):
        self.esp = [0 for _ in range(self.T + 1)]
        for _ in range(self.d - 1):
            self.esp = [deepcopy(self.esp) for _ in range(self.T + 1)]

    def anadeRacional(self, m, n):
        r = Racional(m, n)
        if self.d == 1:
            x = r.posicion(self.T, self.d)
            nx = int(c * self.T - x)
            self.esp[nx] += 1
            total = self.esp[nx]
        elif self.d == 2:
            x, y = r.posicion(self.T, self.d)
            nx = int(c * self.T - x)
            ny = int(c * self.T - y)
            self.esp[nx][ny] += 1
            total = self.esp[nx][ny]
        elif self.d == 3:
            x, y, z = r.posicion(self.T, self.d)
            nx = int(c * self.T - x)
            ny = int(c * self.T - y)
            nz = int(c * self.T - z)
            self.esp[nx][ny][nz] += 1
            total = self.esp[nx][ny][nz]
        if self.max < total:
            self.max = total

    def anadeConjuntoRacional(self, n):
        m = 0
        while m < n:
            self.anadeRacional(m, n)
            m += 1
        if self.d == 1:
            self.esp[0] = 1
        elif self.d == 2:
            self.esp[0][0] = 1
        else:
            self.esp[0][0][0] = 1

    def imprime(self):
        output = ''
        if self.d == 1:
            for nx in range(self.T + 1):
                t = self.esp[nx]
                output += '%d;' % t if t else ';'
        if self.d == 2:
            for ny in range(self.T + 1):
                for nx in range(self.T + 1):
                    t = self.esp[nx][ny]
                    output += '%d;' % t if t else ';'
                output += '\n'
        if self.d == 3:
            for nz in range(self.T + 1):
                for ny in range(self.T + 1):
                    for nx in range(self.T + 1):
                        t = self.esp[nx][ny][nz]
                        output += '%d;' % t if t else ';'
                    output += '\n'
                output += '\n'
        return output

    def histograma2d(self, fname):
        s = svg(height="100%", width="100%")
        s.set_viewBox("0 0 1000 1000")
        oh = ShapeBuilder()
        radio = 1000.0 / (2 * self.T)
        rmin = 5
        for x in range(self.T + 1):
            for y in range(self.T + 1):
                per = self.esp[x][y] / float(self.max)
                px = x * 2 * radio
                py = y * 2 * radio
                if per > 0.0:
                    r = radio * per + rmin * (1 - per)
                    c = oh.createCircle(px, py, r, fill='#000', stroke='none')
                else:
                    c = oh.createCircle(px, py, 1, fill='#F00', stroke='none')
                s.addElement(c)
        s.save(fname)


def divisores():
    esp = Espacio(1, 12)
    divs = divisors(int(pow(2, 12) - 1))
    with open('histograma_1d_2e12.csv', 'wt') as fp:
        for div in divs:
            esp.inicia()
            esp.anadeConjuntoRacional(div)
            linea = '%d;' % div + esp.imprime()
            fp.write(linea + '\n')
            print linea

def histograma2d(d, T, n):
    esp = Espacio(d, T)
    esp.inicia()
    n = int(n)
    esp.anadeConjuntoRacional(n)
    fname = r'C:\Users\enrique\Google Drive\Enrique\ArticuloRacionales\figuras\histograma_%02d_%08d.svg'%(esp.T, n)
    esp.histograma2d(fname)

histograma2d(2, 14, 6242685)
histograma2d(2, 14, 6242685)
