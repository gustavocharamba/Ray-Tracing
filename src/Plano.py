from src.Ponto import Ponto
from src.Vetor import Vetor
from src.Raio import Raio


class Plano:
    """Plano infinito definido por um ponto e uma normal, com material associado.
    Sabe testar se um raio o acerta e retornar a distância t da interseção."""

    def __init__(self, ponto: Ponto, normal: Vetor, material):
        """Cria o plano. O ponto é qualquer ponto sobre ele; a normal é normalizada
        para garantir que os cálculos de produto escalar sejam consistentes."""
        self.ponto = ponto
        self.normal = normal.normalizar()
        self.material = material

    def intersectar(self, raio: Raio):
        """Testa se o raio acerta o plano e retorna o t da interseção.
        Retorna None se o raio for paralelo ao plano ou se a interseção
        ficar atrás da câmera.

        Derivação: todo ponto P no plano satisfaz (P - P0)·N = 0.
        Substituindo P = O + t*D:

            (O + t*D - P0)·N = 0
            t = ((P0 - O)·N) / (D·N)

        Se D·N ≈ 0 o raio é paralelo ao plano — sem interseção válida.
        O epsilon 1e-6 evita divisão por zero e auto-interseção."""
        denom = raio.direcao.prodEscalar(self.normal)
        if abs(denom) < 1e-6:
            return None   # raio paralelo ao plano

        p0_menos_o = self.ponto - raio.origem   # vetor de O até P0 (Ponto - Ponto = Vetor)
        t = p0_menos_o.prodEscalar(self.normal) / denom

        if t > 1e-6:
            return t
        return None

    def normal_em(self, ponto):
        """Normal unitária constante do plano."""
        return self.normal
