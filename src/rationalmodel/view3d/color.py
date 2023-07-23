from madcad import vec3
from madcad.mathutils import lerp


class ColorKnot:
    def __init__(self, alpha: float, value: vec3) -> None:
        self.alpha = alpha
        self.value = value


class ColorLine:
    def __init__(self) -> None:
        self.knots: list[ColorKnot] = []
        self.normalized = False
    
    def add(self, alpha: float, value: vec3) -> None:
        self.knots.append(ColorKnot(alpha, value))
        self.knots.sort(key=lambda x: x.alpha)
        self.normalized = False

    @staticmethod
    def _blend(a: vec3, b: vec3, alpha: float) -> vec3:
        r = lerp(a.x, b.x, alpha)
        g = lerp(a.y, b.y, alpha)
        b = lerp(a.z, b.z, alpha)
        return vec3(r, g, b)

    def normalize(self) -> None:
        if not self.normalized:
            self.normalized = True
            for knot in self.knots:
                knot.alpha = knot.alpha / self.knots[-1].alpha

    def getColor(self, alpha: float) -> vec3:
        self.normalize()
        if alpha <= 0.0:
            return self.knots[0].value
        if alpha >= 1.0:
            return self.knots[-1].value
        for index in range(len(self.knots)):
            if alpha <= self.knots[index].alpha:
                alpha1 = self.knots[index - 1].alpha
                alpha2 = self.knots[index].alpha
                beta = (alpha - alpha1) / (alpha2 - alpha1)
                color = self._blend(
                    self.knots[index - 1].value,
                    self.knots[index].value,
                    beta
                )
                return color
        return vec3(1)
