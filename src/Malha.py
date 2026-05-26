import math
from types import SimpleNamespace

from src.Vetor import Vetor
from src.Matriz import Matriz


class Malha:
    def __init__(self, obj_reader, matriz_transformacao=None, material=None):
        """Inicializa a malha triangular a partir de um ObjReader."""
        vertices_lidos = obj_reader.get_vertices()
        self.n_vertices = len(vertices_lidos)
        if self.n_vertices < 3:
            raise ValueError("O número total de vértices deve ser >= 3.")

        faces_lidas = obj_reader.get_faces()
        self.n_triangulos = len(faces_lidas)
        if self.n_triangulos == 0:
            raise ValueError("A malha deve possuir pelo menos um triângulo.")
        self.material = material

        matriz = matriz_transformacao if matriz_transformacao else Matriz()
        self.matriz_transformacao = matriz
        self.lista_vertices = [matriz.aplicar_ponto(v) for v in vertices_lidos]
        self.normais_obj = [
            self._normalizar_vetor(matriz.aplicar_vetor(n))
            for n in obj_reader.get_normals()
        ]

        self.O_d = self._normalizar_cor(self._cor_difusa(material, obj_reader))
        if not self._material_tem_cor(material):
            self.material = SimpleNamespace(
                color=SimpleNamespace(r=self.O_d.x, g=self.O_d.y, b=self.O_d.z)
            )
        self.lista_indices = []
        self.indices_normais = []
        self.materiais_triangulos = []
        self.normais_triangulos = []
        self.normais_vertices = []
        self.ultimo_indice_triangulo = None
        self.ultimo_barycentrico = None
        self._construir_geometria_e_normais(faces_lidas)

    def _cor_difusa(self, material, obj_reader):
        if self._material_tem_cor(material):
            return Vetor(material.color.r, material.color.g, material.color.b)
        return self._kd_obj(obj_reader)

    def _material_tem_cor(self, material):
        if material is None or not hasattr(material, "color"):
            return False
        cor = material.color
        return bool(getattr(material, "name", "")) or cor.r != 0 or cor.g != 0 or cor.b != 0

    def _kd_obj(self, obj_reader):
        for face in obj_reader.get_faces():
            kd = getattr(face.material, "kd", None)
            if kd is not None and (kd.x != 0 or kd.y != 0 or kd.z != 0):
                return kd
        return obj_reader.get_kd()

    def _normalizar_cor(self, cor):
        return Vetor(
            max(0.0, min(1.0, cor.x)),
            max(0.0, min(1.0, cor.y)),
            max(0.0, min(1.0, cor.z)),
        )

    def _normalizar_vetor(self, vetor, fallback=None):
        mag = math.sqrt(vetor.x ** 2 + vetor.y ** 2 + vetor.z ** 2)
        if mag > 0:
            return Vetor(vetor.x / mag, vetor.y / mag, vetor.z / mag)
        return fallback if fallback is not None else Vetor(0.0, 0.0, 0.0)

    def _construir_geometria_e_normais(self, faces):
        for face in faces:
            if len(face.vertice_indice) != 3:
                raise ValueError("Cada face da malha precisa ter exatamente 3 índices.")
            for idx in face.vertice_indice:
                if idx < 0 or idx >= self.n_vertices:
                    raise ValueError(f"Índice de vértice fora dos limites: {idx}")
            self.lista_indices.append(face.vertice_indice[:])
            self.indices_normais.append(face.normal_indice[:])
            self.materiais_triangulos.append(face.material)

        for indices in self.lista_indices:
            v0 = self.lista_vertices[indices[0]]
            v1 = self.lista_vertices[indices[1]]
            v2 = self.lista_vertices[indices[2]]
            normal = (v1 - v0).prodVetorial(v2 - v0)
            self.normais_triangulos.append(self._normalizar_vetor(normal))

        self.normais_vertices = [Vetor(0.0, 0.0, 0.0) for _ in range(self.n_vertices)]
        contagem_vertices = [0 for _ in range(self.n_vertices)]
        for i in range(self.n_triangulos):
            n = self.normais_triangulos[i]
            for idx in self.lista_indices[i]:
                self.normais_vertices[idx] = self.normais_vertices[idx] + n
                contagem_vertices[idx] += 1

        for i in range(self.n_vertices):
            if contagem_vertices[i] > 0:
                self.normais_vertices[i] = self._normalizar_vetor(
                    self.normais_vertices[i] / contagem_vertices[i],
                    fallback=Vetor(0.0, 1.0, 0.0),
                )
            else:
                self.normais_vertices[i] = Vetor(0.0, 1.0, 0.0)

    def _normal_obj_interpolada(self, indice_triangulo, fallback):
        indices_normais = self.indices_normais[indice_triangulo]
        if self.ultimo_barycentrico is None:
            return fallback
        if any(idx < 0 or idx >= len(self.normais_obj) for idx in indices_normais):
            return None

        w0, w1, w2 = self.ultimo_barycentrico
        normal = (
            self.normais_obj[indices_normais[0]] * w0
            + self.normais_obj[indices_normais[1]] * w1
            + self.normais_obj[indices_normais[2]] * w2
        )
        return self._normalizar_vetor(normal, fallback=fallback)

    def intersectar(self, raio):
        """Retorna o menor t positivo de interseção raio-triângulo."""
        t_min, EPSILON = float("inf"), 1e-6
        indice_atingido = None
        barycentrico = None
        for i, indices in enumerate(self.lista_indices):
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
                indice_atingido = i
                barycentrico = (1.0 - u - v, u, v)

        self.ultimo_indice_triangulo = indice_atingido
        self.ultimo_barycentrico = barycentrico
        return t_min if t_min != float("inf") else None

    def normal_em(self, ponto):
        """Normal no ponto atingido, interpolada pelas normais médias dos vértices."""
        if self.ultimo_indice_triangulo is None:
            return Vetor(0.0, 1.0, 0.0)

        fallback = self.normais_triangulos[self.ultimo_indice_triangulo]
        normal_obj = self._normal_obj_interpolada(self.ultimo_indice_triangulo, fallback)
        if normal_obj is not None:
            return normal_obj

        indices = self.lista_indices[self.ultimo_indice_triangulo]
        if self.ultimo_barycentrico is None:
            return fallback

        w0, w1, w2 = self.ultimo_barycentrico
        normal = (
            self.normais_vertices[indices[0]] * w0
            + self.normais_vertices[indices[1]] * w1
            + self.normais_vertices[indices[2]] * w2
        )
        return self._normalizar_vetor(
            normal,
            fallback=fallback,
        )
