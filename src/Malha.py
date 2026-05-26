import math
from types import SimpleNamespace

from src.Vetor import Vetor
from src.Matriz import Matriz


class Malha:
    TRIANGULOS_POR_FOLHA = 4

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
        self._precalcular_triangulos()
        self.bvh = self._construir_bvh(list(range(self.n_triangulos)))

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

    def _bbox_vertices(self, vertices):
        xs = [v.x for v in vertices]
        ys = [v.y for v in vertices]
        zs = [v.z for v in vertices]
        return (
            (min(xs), min(ys), min(zs)),
            (max(xs), max(ys), max(zs)),
        )

    def _unir_bboxes(self, bbox_a, bbox_b):
        min_a, max_a = bbox_a
        min_b, max_b = bbox_b
        return (
            (
                min(min_a[0], min_b[0]),
                min(min_a[1], min_b[1]),
                min(min_a[2], min_b[2]),
            ),
            (
                max(max_a[0], max_b[0]),
                max(max_a[1], max_b[1]),
                max(max_a[2], max_b[2]),
            ),
        )

    def _bbox_indices_triangulos(self, indices_triangulos):
        bbox = self.bboxes_triangulos[indices_triangulos[0]]
        for indice in indices_triangulos[1:]:
            bbox = self._unir_bboxes(bbox, self.bboxes_triangulos[indice])
        return bbox

    def _eixo_mais_longo(self, bbox):
        minimo, maximo = bbox
        extensoes = (
            maximo[0] - minimo[0],
            maximo[1] - minimo[1],
            maximo[2] - minimo[2],
        )
        return max(range(3), key=lambda eixo: extensoes[eixo])

    def _precalcular_triangulos(self):
        self.bboxes_triangulos = []
        self.centroides_triangulos = []
        self.arestas_triangulos = []

        for indices in self.lista_indices:
            v0 = self.lista_vertices[indices[0]]
            v1 = self.lista_vertices[indices[1]]
            v2 = self.lista_vertices[indices[2]]
            bbox = self._bbox_vertices([v0, v1, v2])
            self.bboxes_triangulos.append(bbox)
            self.centroides_triangulos.append((
                (v0.x + v1.x + v2.x) / 3.0,
                (v0.y + v1.y + v2.y) / 3.0,
                (v0.z + v1.z + v2.z) / 3.0,
            ))
            self.arestas_triangulos.append((v1 - v0, v2 - v0))

    def _construir_bvh(self, indices_triangulos):
        bbox = self._bbox_indices_triangulos(indices_triangulos)

        if len(indices_triangulos) <= self.TRIANGULOS_POR_FOLHA:
            return SimpleNamespace(
                bbox=bbox,
                esquerda=None,
                direita=None,
                indices_triangulos=indices_triangulos,
            )

        eixo = self._eixo_mais_longo(bbox)
        indices_ordenados = sorted(
            indices_triangulos,
            key=lambda indice: self.centroides_triangulos[indice][eixo],
        )
        meio = len(indices_ordenados) // 2

        return SimpleNamespace(
            bbox=bbox,
            esquerda=self._construir_bvh(indices_ordenados[:meio]),
            direita=self._construir_bvh(indices_ordenados[meio:]),
            indices_triangulos=None,
        )

    def _intersectar_bbox(self, raio, bbox, t_limite=float("inf")):
        t_min = -float("inf")
        t_max = t_limite
        minimo, maximo = bbox
        origem = (raio.origem.x, raio.origem.y, raio.origem.z)
        direcao = (raio.direcao.x, raio.direcao.y, raio.direcao.z)

        for eixo in range(3):
            origem_eixo = origem[eixo]
            direcao_eixo = direcao[eixo]

            if abs(direcao_eixo) < 1e-12:
                if origem_eixo < minimo[eixo] or origem_eixo > maximo[eixo]:
                    return None
                continue

            inv_d = 1.0 / direcao_eixo
            t0 = (minimo[eixo] - origem_eixo) * inv_d
            t1 = (maximo[eixo] - origem_eixo) * inv_d
            if t0 > t1:
                t0, t1 = t1, t0

            t_min = max(t_min, t0)
            t_max = min(t_max, t1)
            if t_min > t_max:
                return None

        if t_max <= 1e-6:
            return None
        return max(t_min, 0.0)

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

    def _intersectar_triangulo(self, raio, indice_triangulo, epsilon):
        indices = self.lista_indices[indice_triangulo]
        v0 = self.lista_vertices[indices[0]]
        edge1, edge2 = self.arestas_triangulos[indice_triangulo]
        h = raio.direcao.prodVetorial(edge2)
        a = edge1.prodEscalar(h)

        if -epsilon < a < epsilon:
            return None, None

        f = 1.0 / a
        s = raio.origem - v0
        u = f * s.prodEscalar(h)
        if u < 0.0 or u > 1.0:
            return None, None

        q = s.prodVetorial(edge1)
        v = f * raio.direcao.prodEscalar(q)
        if v < 0.0 or (u + v) > 1.0:
            return None, None

        t = f * edge2.prodEscalar(q)
        if t <= epsilon:
            return None, None

        return t, (1.0 - u - v, u, v)

    def intersectar(self, raio):
        """Retorna o menor t positivo de interseção raio-triângulo."""
        t_min, EPSILON = float("inf"), 1e-6
        indice_atingido = None
        barycentrico = None
        t_bbox_raiz = self._intersectar_bbox(raio, self.bvh.bbox, t_min)
        if t_bbox_raiz is None:
            self.ultimo_indice_triangulo = None
            self.ultimo_barycentrico = None
            return None

        pilha = [(t_bbox_raiz, self.bvh)]
        while pilha:
            _, no = pilha.pop()

            if no.indices_triangulos is not None:
                for indice_triangulo in no.indices_triangulos:
                    t, bary = self._intersectar_triangulo(raio, indice_triangulo, EPSILON)
                    if t is not None and t < t_min:
                        t_min = t
                        indice_atingido = indice_triangulo
                        barycentrico = bary
                continue

            filhos_atingidos = []
            for filho in (no.esquerda, no.direita):
                t_bbox = self._intersectar_bbox(raio, filho.bbox, t_min)
                if t_bbox is not None:
                    filhos_atingidos.append((t_bbox, filho))

            filhos_atingidos.sort(key=lambda item: item[0], reverse=True)
            pilha.extend(filhos_atingidos)

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
