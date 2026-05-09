import math
from types import SimpleNamespace

from src.Vetor import Vetor
from src.Matriz import Matriz


class Malha:
    def __init__(self, obj_reader, matriz_transformacao=None, material=None):
        """Inicializa a malha triangular a partir de um ObjReader."""
        self.n_vertices = len(obj_reader.get_vertices())
        if self.n_vertices < 3:
            raise ValueError("O número total de vértices deve ser >= 3.")

        faces_lidas = obj_reader.get_faces()
        self.n_triangulos = len(faces_lidas)
        if self.n_triangulos == 0:
            raise ValueError("A malha deve possuir pelo menos um triângulo.")
        self.material = material

        matriz = matriz_transformacao if matriz_transformacao else Matriz()
        self.lista_vertices = [matriz.aplicar_ponto(v) for v in obj_reader.get_vertices()]

        self.O_d = self._cor_difusa(material, obj_reader.get_kd())
        if not self._material_tem_cor(material):
            self.material = SimpleNamespace(
                color=SimpleNamespace(r=self.O_d.x, g=self.O_d.y, b=self.O_d.z)
            )
        self.lista_indices = []
        self.normais_triangulos = []
        self.normais_vertices = []
        self._construir_geometria_e_normais(faces_lidas)

    def _cor_difusa(self, material, kd_obj):
        if self._material_tem_cor(material):
            return Vetor(material.color.r, material.color.g, material.color.b)
        return kd_obj

    def _material_tem_cor(self, material):
        if material is None or not hasattr(material, "color"):
            return False
        cor = material.color
        return bool(getattr(material, "name", "")) or cor.r != 0 or cor.g != 0 or cor.b != 0

    def _get_modulo(self, v):
        return math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)

    def _construir_geometria_e_normais(self, faces):
        for face in faces:
            if len(face.vertice_indice) != 3:
                raise ValueError("Cada face da malha precisa ter exatamente 3 índices.")
            for idx in face.vertice_indice:
                if idx < 0 or idx >= self.n_vertices:
                    raise ValueError(f"Índice de vértice fora dos limites: {idx}")
            self.lista_indices.append(face.vertice_indice[:])

        for indices in self.lista_indices:
            v0 = self.lista_vertices[indices[0]]
            v1 = self.lista_vertices[indices[1]]
            v2 = self.lista_vertices[indices[2]]
            normal = (v1 - v0).prodVetorial(v2 - v0)

            mag = self._get_modulo(normal)
            if mag > 0:
                normal = Vetor(normal.x / mag, normal.y / mag, normal.z / mag)
            else:
                normal = Vetor(0.0, 0.0, 0.0)
            self.normais_triangulos.append(normal)

        self.normais_vertices = [Vetor(0.0, 0.0, 0.0) for _ in range(self.n_vertices)]
        for i in range(self.n_triangulos):
            n = self.normais_triangulos[i]
            for idx in self.lista_indices[i]:
                self.normais_vertices[idx] = self.normais_vertices[idx] + n

        for i in range(self.n_vertices):
            mag = self._get_modulo(self.normais_vertices[i])
            if mag > 0:
                nv = self.normais_vertices[i]
                self.normais_vertices[i] = Vetor(nv.x / mag, nv.y / mag, nv.z / mag)
            else:
                self.normais_vertices[i] = Vetor(0, 1, 0)

    def intersectar(self, raio):
        """Retorna o menor t positivo de interseção raio-triângulo."""
        t_min, EPSILON = float("inf"), 1e-6
        for indices in self.lista_indices:
            v0 = self.lista_vertices[indices[0]]
            v1 = self.lista_vertices[indices[1]]
            v2 = self.lista_vertices[indices[2]]
            edge1, edge2 = v1 - v0, v2 - v0
            h = raio.direcao.prodVetorial(edge2)
            a = edge1.prodEscalar(h)

            if -EPSILON < a < EPSILON:
                continue
            f = 1.0 / a
            s = raio.origem - v0
            u = f * s.prodEscalar(h)
            if u < 0.0 or u > 1.0:
                continue
            q = s.prodVetorial(edge1)
            v = f * raio.direcao.prodEscalar(q)
            if v < 0.0 or (u + v) > 1.0:
                continue
            t = f * edge2.prodEscalar(q)

            if EPSILON < t < t_min:
                t_min = t
        return t_min if t_min != float("inf") else None
