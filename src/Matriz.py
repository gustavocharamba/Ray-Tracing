import math

from src.Ponto import Ponto
from src.Vetor import Vetor


class Matriz:
    """Matriz 4x4 para transformações afins em coordenadas homogêneas."""

    def __init__(self, dados=None):
        if dados is None:
            self.dados = [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        else:
            if len(dados) != 4 or any(len(linha) != 4 for linha in dados):
                raise ValueError("Matriz de transformação deve ter dimensões 4x4.")
            self.dados = [[float(valor) for valor in linha] for linha in dados]

    def __matmul__(self, outra):
        if not isinstance(outra, Matriz):
            raise TypeError("Multiplicação de matrizes espera outra instância de Matriz.")
        resultado = [[0.0 for _ in range(4)] for _ in range(4)]
        for i in range(4):
            for j in range(4):
                resultado[i][j] = sum(self.dados[i][k] * outra.dados[k][j] for k in range(4))
        return Matriz(resultado)

    def __repr__(self):
        return f"Matriz({self.dados})"

    def aplicar_ponto(self, ponto: Ponto) -> Ponto:
        x, y, z = ponto.x, ponto.y, ponto.z
        valores = [
            self.dados[0][0] * x + self.dados[0][1] * y + self.dados[0][2] * z + self.dados[0][3],
            self.dados[1][0] * x + self.dados[1][1] * y + self.dados[1][2] * z + self.dados[1][3],
            self.dados[2][0] * x + self.dados[2][1] * y + self.dados[2][2] * z + self.dados[2][3],
            self.dados[3][0] * x + self.dados[3][1] * y + self.dados[3][2] * z + self.dados[3][3],
        ]
        w = valores[3]
        if abs(w) > 1e-12 and abs(w - 1.0) > 1e-12:
            return Ponto(valores[0] / w, valores[1] / w, valores[2] / w)
        return Ponto(valores[0], valores[1], valores[2])

    def aplicar_vetor(self, vetor: Vetor) -> Vetor:
        x, y, z = vetor.x, vetor.y, vetor.z
        return Vetor(
            self.dados[0][0] * x + self.dados[0][1] * y + self.dados[0][2] * z,
            self.dados[1][0] * x + self.dados[1][1] * y + self.dados[1][2] * z,
            self.dados[2][0] * x + self.dados[2][1] * y + self.dados[2][2] * z,
        )

    @staticmethod
    def translacao(dx, dy, dz):
        return Matriz([
            [1.0, 0.0, 0.0, dx],
            [0.0, 1.0, 0.0, dy],
            [0.0, 0.0, 1.0, dz],
            [0.0, 0.0, 0.0, 1.0],
        ])

    @staticmethod
    def escala(sx, sy, sz):
        return Matriz([
            [sx, 0.0, 0.0, 0.0],
            [0.0, sy, 0.0, 0.0],
            [0.0, 0.0, sz, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])

    @staticmethod
    def rotacao_x(angulo):
        c, s = math.cos(angulo), math.sin(angulo)
        return Matriz([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, c, -s, 0.0],
            [0.0, s, c, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])

    @staticmethod
    def rotacao_y(angulo):
        c, s = math.cos(angulo), math.sin(angulo)
        return Matriz([
            [c, 0.0, s, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [-s, 0.0, c, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])

    @staticmethod
    def rotacao_z(angulo):
        c, s = math.cos(angulo), math.sin(angulo)
        return Matriz([
            [c, -s, 0.0, 0.0],
            [s, c, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])

    @staticmethod
    def rotacao(rx, ry, rz):
        return Matriz.rotacao_z(rz) @ Matriz.rotacao_y(ry) @ Matriz.rotacao_x(rx)
