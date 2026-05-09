import sys
from pathlib import Path

from src.Ponto import Ponto
from src.Vetor import Vetor
from src.Raio import Raio
from src.Esfera import Esfera
from src.Plano import Plano
from src.Malha import Malha
from src.Matriz import Matriz
from utils.Scene.sceneParser import SceneJsonLoader
from utils.MeshReader.ObjReader import ObjReader

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
            if transform.t_type == "translation":
                atual = Matriz.translacao(dados.x, dados.y, dados.z)
            elif transform.t_type == "scaling":
                atual = Matriz.escala(dados.x, dados.y, dados.z)
            elif transform.t_type == "rotation":
                atual = Matriz.rotacao(dados.x, dados.y, dados.z)
            else:
                continue
            matriz = atual @ matriz
        return matriz

    pos = obj.relative_pos
    return Matriz.translacao(pos.x, pos.y, pos.z)

def criar_objetos(scene, scene_file_path):
    objetos = []
    project_root = Path(__file__).resolve().parent
    scene_dir = Path(scene_file_path).resolve().parent

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

            nome_arquivo = Path(rel_path).name
            tentativas = [
                (scene_dir / rel_path).resolve(),
                (project_root / rel_path).resolve(),
                (project_root / "utils" / "input" / nome_arquivo).resolve(),
                (project_root / "utils" / "inputs" / nome_arquivo).resolve()
            ]

            full_path = next((p for p in tentativas if p.exists()), None)

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

def renderizar(scene_path="utils/input/monkeyScene.json", output_path="out.ppm"):
    scene   = SceneJsonLoader.load_file(scene_path)
    largura = scene.camera.image_width
    altura  = scene.camera.image_height
    d       = scene.camera.screen_distance

    C, u, v, w = base_camera(scene)
    objetos     = criar_objetos(scene, scene_path)

    print(f"Iniciando renderização ({largura}x{altura})...")
    with open(output_path, "w", encoding="ascii", newline='\n') as f:
        f.write(f"P3\n{largura} {altura}\n255\n")
        for j in range(altura):
            for i in range(largura):
                raio = gerar_raio(i, j, C, u, v, w, largura, altura, d)
                t_min, material_atingido = float("inf"), None
                for obj in objetos:
                    t = obj.intersectar(raio)
                    if t is not None and t < t_min:
                        t_min, material_atingido = t, obj.material

                if material_atingido:
                    r = int(max(0, min(255, material_atingido.color.r * 255)))
                    g = int(max(0, min(255, material_atingido.color.g * 255)))
                    b = int(max(0, min(255, material_atingido.color.b * 255)))
                else:
                    r = g = b = 0
                f.write(f"{r} {g} {b}\n")
    print(f"Render finalizado: {output_path}")

if __name__ == "__main__":
    scene_file = sys.argv[1] if len(sys.argv) > 1 else "utils/input/monkeyScene.json"
    renderizar(scene_file)
