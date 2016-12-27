import svgwrite
from svgwrite import rgb

class Ejes():
    def __init__(self, T):
        self.T = T
        
    def dibuja(self, malla, dwg, todo):
        ejes = todo.add(dwg.g(id='ejes'))
        (x1, y1) = malla.obtienePosN(0, self.T)
        (x2, y2) = malla.obtienePosN(self.T, self.T)
        y1 = 0.0
        ejes.add(dwg.line((x1, y1), (x2, y1), stroke=rgb(0, 0, 0, '%'), stroke_width=0.05, stroke_dasharray=[0.1, 0.2]))
        ejes.add(dwg.line((0.0, y1), (0.0, y2), stroke=rgb(0, 0, 0, '%'), stroke_width=0.05, stroke_dasharray=[0.1, 0.2]))
    
class Camino():
    def __init__(self, sec, color=rgb(0, 0, 0, '%'), grueso=0.05, dasharray=[], puntos=True):
        self.sec = sec
        self.color = color
        self.grueso = grueso
        self.dasharray=dasharray
        self.puntos = puntos
        
    def obtieneVelocidad(self, malla):
        (x1, y1) = (0, 0)
        n = 0
        l = len(self.sec)
        for t in range(l):
            n += int(self.sec[t])
        (x2, y2) = malla.obtienePosN(n, t+1)
        return (x2-x1)/(y2-y1)
        
    def dibuja(self, malla, dwg, todo):
        (x1, y1) = (0, 0)
        path = todo.add(dwg.g(id='path'))
        
        n = 0
        for t in range(malla.T):
            n += int(self.sec[t%(len(self.sec))])
            (x2, y2) = malla.obtienePosN(n, t+1)
            path.add(dwg.line((x1, y1), (x2, y2), stroke=self.color, stroke_width=self.grueso, stroke_dasharray=self.dasharray))
            (x1, y1) = (x2, y2)
        
        if self.puntos:
            n = 0
            (x1, y1) = (0, 0)
            for t in range(malla.T):
                path.add(dwg.circle(center=(x1, y1), r=0.25, stroke_width=0.05, stroke=rgb(0, 0, 0, '%'), fill=rgb(0, 0, 0, '%')))
                n += int(self.sec[t%(len(self.sec))])
                (x1, y1) = malla.obtienePosN(n, t+1)
            path.add(dwg.circle(center=(x1, y1), r=0.25, stroke_width=0.05, stroke=rgb(0, 0, 0, '%'), fill=rgb(0, 0, 0, '%')))

class Linea():
    def __init__(self, color=rgb(0, 0, 0, '%'), grueso=0.05, dasharray=[]):
        self.color = color
        self.grueso = grueso
        self.dasharray = dasharray
        self.puntos = [(0, 0)]
        
    def anadePunto(self, (x, y)):
        self.puntos.append((x, y))
        
    def dibuja(self, dwg, grupo):
        if len(self.puntos) < 2:
            return
        (x1, y1) = self.puntos[0]
        for n in range(1, len(self.puntos)):
            (x2, y2) = self.puntos[n]
            grupo.add(dwg.line((x1, y1), (x2, y2), stroke=self.color, stroke_width=self.grueso, stroke_dasharray=self.dasharray))
            (x1, y1) = (x2, y2)
    
class Fila():
    def __init__(self, T):
        self.T = T
        self.offset = 0.0
        
    def poneOffset(self, offset):
        self.offset = offset
        
    def obtienePosN(self, n):
        return (0.5*float(self.T) - float(n) + self.offset, float(self.T))
    
    def obtienePos(self, x):
        return (x + self.offset, self.T)
        
    def dibuja(self, dwg, grupo):
        for i in range(self.T+1):
            (x, y) = self.obtienePosN(i)
            grupo.add(dwg.circle(center=(x, y), r=0.25, stroke_width=0.05, stroke=rgb(0, 0, 0, '%'), fill=rgb(255, 255, 255, '%')))
    
class Malla():
    def __init__(self, T):
        self.T = T
        self.filas = []
        for i in range(T+1):
            self.filas.append(Fila(i))
        
    def obtienePosN(self, n, t):
        return self.filas[int(t)].obtienePosN(n)
    
    def obtienePos(self, x, t):
        return self.filas[int(t)].obtienePos(x)
    
    def poneVelocidad(self, v):
        offset = 0.0        
        for i in range(len(self.filas)):
            self.filas[i].poneOffset(offset)
            offset -= v
    
    def dibuja(self, dwg, todo):
        malla = todo.add(dwg.g(id='malla'))
        for i in range(len(self.filas)):
            self.filas[i].dibuja(dwg, malla)


class Dibujo():
    def __init__(self, T):
        self.T = T
        self.ejes = Ejes(T)
        self.lineas = []
        self.caminosDebajo = []
        self.malla = Malla(T)
        self.caminosEncima = []
        
    def obtieneMalla(self):
        return self.malla
        
    def anadeCaminoEncima(self, camino):
        self.caminosEncima.append(camino)
        
    def anadeCaminoDebajo(self, camino):
        self.caminosDebajo.append(camino)
        
    def poneVelocidad(self, v):
        self.malla.poneVelocidad(v)
        
    def anadeLinea(self, linea):
        self.lineas.append(linea)
        
    def obtienePos(self, x, t):
        return self.malla.obtienePos(x, t)

    def dibuja(self, nombre):
        (x1, _ ) = self.malla.obtienePosN(0, self.T)
        (x2, y2) = self.malla.obtienePosN(self.T, self.T)
        viewbox=u'%f %f %f %f'%(x2-1, -1, x1-x2+2, y2+2)
        dwg = svgwrite.Drawing(nombre, size=('10cm', '10cm'), viewBox=(viewbox))
        todo = dwg.add(dwg.g(id='todo'))
        todo.scale(1, -1)
        todo.translate(0, x2-x1)

        self.ejes.dibuja(self.malla, dwg, todo)
        for linea in self.lineas:
            linea.dibuja(dwg, todo)
        for camino in self.caminosDebajo:
            camino.dibuja(self.malla, dwg, todo)
        self.malla.dibuja(dwg, todo)
        for camino in self.caminosEncima:
            camino.dibuja(self.malla, dwg, todo)
        
        dwg.save()
        
        
def lagrangianaDesplazada():
    dibujo = Dibujo(18)
    camino = Camino('101101')
    dibujo.anadeCaminoEncima(camino)
    v = camino.obtieneVelocidad(dibujo.obtieneMalla())
    dibujo.poneVelocidad(v)
    
    linea = Linea(color=rgb(34, 126, 34, '%'))
    linea.anadePunto(dibujo.obtienePos(v*float(18), 18))
    dibujo.anadeLinea(linea)
    
    caminomax = Camino('111100', color=rgb(148, 40, 40, '%'), grueso=0.05, dasharray=[0.1, 0.2])
    dibujo.anadeCaminoDebajo(caminomax)
    caminomin = Camino('001111', color=rgb(148, 40, 40, '%'), grueso=0.05, dasharray=[0.1, 0.2])
    dibujo.anadeCaminoDebajo(caminomin)
    
    dibujo.dibuja(r'C:\Users\enrique\Dropbox\Enrique\Articulo\figuras\Lagrangiana desplazada.svg')
        

def mallaBase():
    dibujo = Dibujo(18)
    dibujo.dibuja(r'C:\Users\enrique\Dropbox\Enrique\Articulo\figuras\Malla.svg')

def pathEn10Pasos(): 
    dibujo = Dibujo(20)
    camino = Camino('0110010001')
    dibujo.anadeCaminoEncima(camino)
    linea = Linea(color=rgb(34, 126, 34, '%'))
    v = camino.obtieneVelocidad(dibujo.obtieneMalla())
    linea.anadePunto(dibujo.obtienePos(v*float(20), 20))
    dibujo.anadeLinea(linea)
    
    dibujo.dibuja(r'C:\Users\enrique\Dropbox\Enrique\ArticuloRacionales\figuras\path10pasos.svg')

pathEn10Pasos()
