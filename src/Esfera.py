import math
from src.Ponto import Ponto
from src.Raio import Raio


class Esfera:
    """Esfera definida por centro, raio e material.
    Sabe testar se um raio a acerta e retornar a distância t da interseção."""

    def __init__(self, centro: Ponto, raio: float, material):
        """Cria a esfera com centro, raio geométrico e material (carrega cor e propriedades)."""
        self.centro = centro
        self.raio = raio
        self.material = material

    def intersectar(self, raio: Raio):
        """Testa se o raio acerta a esfera e retorna o t da interseção mais próxima.
        Retorna None se não houver colisão.

        Derivação: substituindo P = O + t*D na equação da esfera |P - C|² = r²
        e chamando oc = O - C, chegamos à quadrática:

            a*t² + b*t + c = 0
            a = D·D
            b = 2*(oc·D)
            c = (oc·oc) - r²

        O discriminante Δ = b²-4ac decide o resultado:
            Δ < 0  →  raio passa fora, sem colisão
            Δ = 0  →  raio tangencia a esfera (1 ponto)
            Δ > 0  →  raio atravessa a esfera (2 pontos: entrada t1 e saída t2)

        Sempre retornamos o menor t positivo (ponto de entrada, mais próximo da câmera).
        O epsilon 1e-6 evita auto-interseção por imprecisão de ponto flutuante."""
        oc = raio.origem - self.centro   # vetor da origem do raio ao centro da esfera
        a = raio.direcao.prodEscalar(raio.direcao)
        b = 2.0 * oc.prodEscalar(raio.direcao)
        c = oc.prodEscalar(oc) - self.raio ** 2

        discriminante = b * b - 4 * a * c
        if discriminante < 0:
            return None

        raiz = math.sqrt(discriminante)
        t1 = (-b - raiz) / (2 * a)   # interseção mais próxima (entrada)
        t2 = (-b + raiz) / (2 * a)   # interseção mais distante (saída)

        EPS = 1e-6
        if t1 > EPS:
            return t1
        if t2 > EPS:
            return t2
        return None

    def normal_em(self, ponto: Ponto):
        """Normal unitária da esfera no ponto de interseção."""
        return (ponto - self.centro).normalizar()
