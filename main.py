import subprocess
import sys
from pathlib import Path

from src.Raio import Raio
from src.Vetor import Vetor
from src.Esfera import Esfera
from src.Plano import Plano
from src.Malha import Malha
from src.Matriz import Matriz
from utils.Scene.sceneParser import SceneJsonLoader
from utils.MeshReader.ObjReader import ObjReader

EPSILON_SOMBRA = 1e-4

def base_camera(data):
    C    = data.camera.lookfrom
    M    = data.camera.lookat
    v_up = data.camera.up_vector
    w = (C - M).normalizar()
    u = w.prodVetorial(v_up).normalizar()
    v = u.prodVetorial(w)
    return C, u, v, w

def gerar_raio(i, j, C, u, v, w, largura, altura, d):
    aspect = largura / altura
    px = (2 * (i + 0.5) / largura  - 1) * aspect
    py =  1 - 2 * (j + 0.5) / altura
    direcao = ((-w) * d + u * px + v * py).normalizar()
    return Raio(C, direcao)

def matriz_transformacao(obj):
    matriz = Matriz()
    if obj.transforms:
        for transform in obj.transforms:
            dados = transform.data
            tipo = transform.t_type.lower()
            if tipo in ("translation", "translate", "translacao"):
                atual = Matriz.translacao(dados.x, dados.y, dados.z)
            elif tipo in ("scaling", "scale", "escala"):
                atual = Matriz.escala(dados.x, dados.y, dados.z)
            elif tipo in ("rotation", "rotate", "rotacao"):
                atual = Matriz.rotacao(dados.x, dados.y, dados.z)
            else:
                raise ValueError(f"Transformação desconhecida: {transform.t_type}")
            matriz = atual @ matriz
        return matriz

    pos = obj.relative_pos
    return Matriz.translacao(pos.x, pos.y, pos.z)

def resolver_caminho_obj(rel_path, scene_file_path):
    project_root = Path(__file__).resolve().parent
    scene_dir = Path(scene_file_path).resolve().parent
    obj_path = Path(rel_path)
    nome_arquivo = obj_path.name

    tentativas = [
        (scene_dir / obj_path).resolve(),
        (project_root / obj_path).resolve(),
        (project_root / "utils" / "input" / obj_path).resolve(),
        (project_root / "utils" / "input" / nome_arquivo).resolve(),
        (project_root / "utils" / "inputs" / nome_arquivo).resolve(),
    ]

    stem_sem_digitos = obj_path.stem.rstrip("0123456789")
    if stem_sem_digitos and stem_sem_digitos != obj_path.stem:
        nome_sem_digitos = f"{stem_sem_digitos}{obj_path.suffix}"
        tentativas.extend([
            (scene_dir / nome_sem_digitos).resolve(),
            (project_root / "utils" / "input" / nome_sem_digitos).resolve(),
            (project_root / "utils" / "inputs" / nome_sem_digitos).resolve(),
        ])

    return next((p for p in tentativas if p.exists()), None)

def criar_objetos(scene, scene_file_path):
    objetos = []

    for obj in scene.objects:
        posicao = obj.relative_pos

        if obj.obj_type == "sphere":
            raio = obj.numeric_data.get("radius", 1.0)
            objetos.append(Esfera(posicao, raio, obj.material))

        elif obj.obj_type == "plane":
            normal = obj.vetor_point_data.get("normal")
            if normal is None:
                print("ERRO: plano sem normal.")
                continue
            objetos.append(Plano(posicao, normal, obj.material))

        elif obj.obj_type == "mesh":
            rel_path = obj.other_properties.get("path")
            if not rel_path:
                continue

            full_path = resolver_caminho_obj(rel_path, scene_file_path)

            if not full_path:
                print(f"ERRO: Arquivo não encontrado: {rel_path}")
                continue

            try:
                leitor = ObjReader(str(full_path))
                transformacao = matriz_transformacao(obj)
                malha = Malha(leitor, matriz_transformacao=transformacao, material=obj.material)
                objetos.append(malha)
                print(f"{full_path.name} carregado: {malha.n_triangulos} triângulos, {malha.n_vertices} vértices.")
            except Exception as e:
                print(f"Erro ao processar {full_path.name}: {e}")

    return objetos

def cor_para_vetor(cor):
    return Vetor(
        float(getattr(cor, "r", getattr(cor, "x", 0.0))),
        float(getattr(cor, "g", getattr(cor, "y", 0.0))),
        float(getattr(cor, "b", getattr(cor, "z", 0.0))),
    )

def multiplicar_componentes(a, b):
    return Vetor(a.x * b.x, a.y * b.y, a.z * b.z)

def limitar_cor(cor):
    return Vetor(
        max(0.0, min(1.0, cor.x)),
        max(0.0, min(1.0, cor.y)),
        max(0.0, min(1.0, cor.z)),
    )

def material_para_vetor(material, atributo, padrao=None):
    valor = getattr(material, atributo, None)
    if valor is None:
        return padrao if padrao is not None else Vetor(0.0, 0.0, 0.0)
    return cor_para_vetor(valor)

def coeficiente_difuso(obj):
    if hasattr(obj, "O_d"):
        return obj.O_d
    return material_para_vetor(obj.material, "color")

def normal_orientada(obj, ponto, raio):
    normal = obj.normal_em(ponto)
    if normal.modulo() == 0:
        normal = Vetor(0.0, 1.0, 0.0)
    else:
        normal = normal.normalizar()
    if normal.prodEscalar(raio.direcao) > 0:
        normal = -normal
    return normal

def encontrar_intersecao(raio, objetos):
    t_min, obj_atingido = float("inf"), None
    for obj in objetos:
        t = obj.intersectar(raio)
        if t is not None and t < t_min:
            t_min, obj_atingido = t, obj
    if obj_atingido is None:
        return None, None
    return obj_atingido, t_min

def esta_em_sombra(ponto, normal, direcao_luz, distancia_luz, objetos):
    deslocamento = normal if normal.prodEscalar(direcao_luz) >= 0 else -normal
    origem_sombra = ponto + deslocamento * EPSILON_SOMBRA
    raio_sombra = Raio(origem_sombra, direcao_luz)

    for obj in objetos:
        t = obj.intersectar(raio_sombra)
        if t is not None and EPSILON_SOMBRA < t < distancia_luz - EPSILON_SOMBRA:
            return True
    return False

def iluminar_phong(obj, ponto, normal, raio, scene, objetos):
    material = obj.material
    ia = cor_para_vetor(scene.global_light.color)
    ka = material_para_vetor(material, "ka")
    kd = coeficiente_difuso(obj)
    ks = material_para_vetor(material, "ks")
    eta = max(float(getattr(material, "ns", 1.0)), 1.0)

    cor = multiplicar_componentes(ka, ia)
    observador = (raio.origem - ponto).normalizar()

    for luz in scene.light_list:
        vetor_luz = luz.pos - ponto
        distancia_luz = vetor_luz.modulo()
        if distancia_luz <= EPSILON_SOMBRA:
            continue

        direcao_luz = vetor_luz / distancia_luz
        n_dot_l = max(0.0, normal.prodEscalar(direcao_luz))
        if n_dot_l <= 0.0:
            continue

        if esta_em_sombra(ponto, normal, direcao_luz, distancia_luz, objetos):
            continue

        il = cor_para_vetor(luz.color)
        difusa = multiplicar_componentes(il, kd) * n_dot_l

        reflexao = (normal * (2.0 * n_dot_l) - direcao_luz).normalizar()
        r_dot_v = max(0.0, reflexao.prodEscalar(observador))
        especular = multiplicar_componentes(il, ks) * (r_dot_v ** eta)

        cor = cor + difusa + especular

    return limitar_cor(cor)

def renderizar(scene_path="utils/input/entrega2Scene.json", output_path="out.ppm"):
    scene   = SceneJsonLoader.load_file(scene_path)
    largura = scene.camera.image_width
    altura  = scene.camera.image_height
    d       = scene.camera.screen_distance

    C, u, v, w = base_camera(scene)
    objetos     = criar_objetos(scene, scene_path)

    print(f"Iniciando renderização ({largura}x{altura})...", flush=True)
    with open(output_path, "w", encoding="ascii", newline='\n') as f:
        f.write(f"P3\n{largura} {altura}\n255\n")
        for j in range(altura):
            for i in range(largura):
                raio = gerar_raio(i, j, C, u, v, w, largura, altura, d)
                obj_atingido, t = encontrar_intersecao(raio, objetos)

                if obj_atingido:
                    ponto = raio.ponto_em(t)
                    normal = normal_orientada(obj_atingido, ponto, raio)
                    cor = iluminar_phong(obj_atingido, ponto, normal, raio, scene, objetos)
                    r = int(cor.x * 255)
                    g = int(cor.y * 255)
                    b = int(cor.z * 255)
                else:
                    r = g = b = 0
                f.write(f"{r} {g} {b}\n")
    print(f"Render finalizado: {output_path}", flush=True)

def converter_saida_ppm(output_path):
    script_convert = Path(__file__).resolve().parent / "utils" / "convert_ppm.py"
    try:
        sys.stdout.flush()
        subprocess.run([sys.executable, str(script_convert), output_path], check=True)
    except Exception as e:
        print(f"ERRO ao converter PPM para JPG: {e}")

if __name__ == "__main__":
    scene_file = sys.argv[1] if len(sys.argv) > 1 else "utils/input/caso3.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "out.ppm"
    renderizar(scene_file, output_file)
    converter_saida_ppm(output_file)
