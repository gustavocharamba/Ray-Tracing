from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple

from src.Ponto import Ponto
from src.Vetor import Vetor
from utils.Scene.sceneSchema import (
    CameraData, ColorData, LightData, MaterialData,
    ObjectData, SceneData, TransformData,
)


class SceneJsonLoader:

    @staticmethod
    def load_file(filename: str) -> SceneData:
        path = Path(filename)
        if not path.exists():
            raise FileNotFoundError(f"Scene file not found: {filename}")
        with open(path, "r", encoding="utf-8") as f:
            root = json.load(f)
        return SceneJsonLoader._build(root)

    @staticmethod
    def load_string(text: str) -> SceneData:
        root = json.loads(text)
        return SceneJsonLoader._build(root)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_triple(value, what: str) -> Tuple[float, float, float]:
        """Aceita [a, b, c] ou {"x":..,"y":..,"z":..} ou {"r":..,"g":..,"b":..}."""
        if isinstance(value, list):
            if len(value) != 3:
                raise ValueError(f"Esperado 3 valores para {what}, obtido {len(value)}")
            return float(value[0]), float(value[1]), float(value[2])
        if isinstance(value, dict):
            if all(k in value for k in ("x", "y", "z")):
                return float(value["x"]), float(value["y"]), float(value["z"])
            if all(k in value for k in ("r", "g", "b")):
                return float(value["r"]), float(value["g"]), float(value["b"])
        raise ValueError(f"Esperado vetor de 3 componentes para {what}")

    @staticmethod
    def _parse_color(value, what="color") -> ColorData:
        r, g, b = SceneJsonLoader._read_triple(value, what)
        return ColorData(r, g, b)

    @staticmethod
    def _parse_vetor(value, what="vector") -> Vetor:
        x, y, z = SceneJsonLoader._read_triple(value, what)
        return Vetor(x, y, z)

    @staticmethod
    def _parse_ponto(value, what="point") -> Ponto:
        x, y, z = SceneJsonLoader._read_triple(value, what)
        return Ponto(x, y, z)

    @staticmethod
    def _is_triplet(value) -> bool:
        return (isinstance(value, list) and len(value) == 3
                and all(isinstance(v, (int, float)) for v in value))

    # ------------------------------------------------------------------
    # Seções do JSON
    # ------------------------------------------------------------------

    @staticmethod
    def _make_default_material(name: str = "") -> MaterialData:
        return MaterialData(
            name=name,
            color=ColorData(0, 0, 0),
            ks=ColorData(0, 0, 0),
            ka=ColorData(0, 0, 0),
            kr=ColorData(0, 0, 0),
            kt=ColorData(0, 0, 0),
            ns=1.0, ni=1.0, d=1.0,
        )

    @staticmethod
    def _parse_material_object(node: dict, fallback_name: str = "") -> MaterialData:
        m = SceneJsonLoader._make_default_material(fallback_name)
        if "name"  in node: m.name  = str(node["name"])
        if "color" in node: m.color = SceneJsonLoader._parse_color(node["color"], f"{m.name}.color")
        if "kd"    in node: m.color = SceneJsonLoader._parse_color(node["kd"],    f"{m.name}.kd")
        if "ka"    in node: m.ka    = SceneJsonLoader._parse_color(node["ka"],    f"{m.name}.ka")
        if "ks"    in node: m.ks    = SceneJsonLoader._parse_color(node["ks"],    f"{m.name}.ks")
        if "kr"    in node: m.kr    = SceneJsonLoader._parse_color(node["kr"],    f"{m.name}.kr")
        if "kt"    in node: m.kt    = SceneJsonLoader._parse_color(node["kt"],    f"{m.name}.kt")
        if "ns"    in node: m.ns    = float(node["ns"])
        if "ni"    in node: m.ni    = float(node["ni"])
        if "d"     in node: m.d     = float(node["d"])
        return m

    @staticmethod
    def _parse_materials(node: dict) -> Dict[str, MaterialData]:
        if not isinstance(node, dict):
            raise ValueError("'materials' deve ser um objeto JSON")
        return {
            name: SceneJsonLoader._parse_material_object(mat_node, name)
            for name, mat_node in node.items()
        }

    @staticmethod
    def _resolve_material(value, table: Dict[str, MaterialData]) -> MaterialData:
        if isinstance(value, str):
            if value not in table:
                raise ValueError(f"Material desconhecido: {value!r}")
            return table[value]
        if isinstance(value, dict):
            name = value.get("name", "")
            return SceneJsonLoader._parse_material_object(value, name)
        raise ValueError("Formato de material inválido (deve ser string ou objeto)")

    @staticmethod
    def _parse_camera(node: dict) -> CameraData:
        cam = CameraData()
        if "image_width"     in node: cam.image_width     = int(node["image_width"])
        if "image_height"    in node: cam.image_height    = int(node["image_height"])
        if "screen_distance" in node: cam.screen_distance = float(node["screen_distance"])
        if "lookfrom"        in node: cam.lookfrom = SceneJsonLoader._parse_ponto(node["lookfrom"], "camera.lookfrom")
        if "lookat"          in node: cam.lookat   = SceneJsonLoader._parse_ponto(node["lookat"],   "camera.lookat")
        # Suporta "upVector" (arquivos JSON) e "vup" (alias C++)
        for key in ("upVector", "vup", "up_vector"):
            if key in node:
                cam.up_vector = SceneJsonLoader._parse_vetor(node[key], f"camera.{key}")
                break
        return cam

    @staticmethod
    def _parse_light(node: dict) -> LightData:
        light = LightData()
        if "name"     in node and isinstance(node["name"], str):
            light.extra_data["name"] = node["name"]
        if "position" in node:
            light.pos   = SceneJsonLoader._parse_ponto(node["position"], "light.position")
        if "color"    in node:
            light.color = SceneJsonLoader._parse_color(node["color"],    "light.color")
        for key, val in node.items():
            if key in ("name", "position", "color"):
                continue
            if isinstance(val, str):
                light.extra_data[key] = val
            elif isinstance(val, (int, float)):
                light.extra_data[key] = str(val)
            elif isinstance(val, bool):
                light.extra_data[key] = "true" if val else "false"
        return light

    @staticmethod
    def _parse_transform(node: dict) -> TransformData:
        if "type" not in node:
            raise ValueError("Entrada de transform sem campo 'type'")
        t = TransformData(t_type=str(node["type"]))
        for key, val in node.items():
            if key == "type":
                continue
            t.data = SceneJsonLoader._parse_vetor(val, f"transform.{key}")
            break
        return t

    _POSITION_HINTS = frozenset({
        "center", "position", "point", "origin",
        "point_on_plane", "relativePos", "relative_pos",
    })

    @staticmethod
    def _parse_object(node: dict, materials: Dict[str, MaterialData]) -> ObjectData:
        if "type" not in node:
            raise ValueError("Objeto sem campo obrigatório: 'type'")

        obj = ObjectData(obj_type=str(node["type"]))

        if "name"        in node: obj.other_properties["name"] = str(node["name"])
        if "material"    in node: obj.material     = SceneJsonLoader._resolve_material(node["material"], materials)
        if "transform"   in node: obj.transforms   = [SceneJsonLoader._parse_transform(t) for t in node["transform"]]
        if "relativePos" in node: obj.relative_pos = SceneJsonLoader._parse_ponto(node["relativePos"], "object.relativePos")

        for key, val in node.items():
            if key in ("type", "material", "transform", "name", "relativePos"):
                continue
            if isinstance(val, bool):
                obj.other_properties[key] = "true" if val else "false"
            elif isinstance(val, (int, float)):
                obj.numeric_data[key] = float(val)
            elif isinstance(val, str):
                obj.other_properties[key] = val
            elif SceneJsonLoader._is_triplet(val):
                v = SceneJsonLoader._parse_vetor(val, f"object.{key}")
                obj.vetor_point_data[key] = v
                if key in SceneJsonLoader._POSITION_HINTS:
                    obj.relative_pos = Ponto(v.x, v.y, v.z)
            elif isinstance(val, list) or isinstance(val, dict):
                pass  # estruturas complexas ignoradas (ex: listas de faces inline)

        return obj

    # ------------------------------------------------------------------

    @staticmethod
    def _build(root: dict) -> SceneData:
        if not isinstance(root, dict):
            raise ValueError("Valor JSON raiz deve ser um objeto")

        scene = SceneData()
        materials: Dict[str, MaterialData] = {}

        if "globalLight" in root:
            scene.global_light.color = SceneJsonLoader._parse_color(root["globalLight"], "globalLight")

        if "materials" in root:
            materials = SceneJsonLoader._parse_materials(root["materials"])

        if "camera" in root:
            scene.camera = SceneJsonLoader._parse_camera(root["camera"])

        if "lights" in root:
            if not isinstance(root["lights"], list):
                raise ValueError("'lights' deve ser um array")
            scene.light_list = [SceneJsonLoader._parse_light(l) for l in root["lights"]]

        if "objects" in root:
            if not isinstance(root["objects"], list):
                raise ValueError("'objects' deve ser um array")
            scene.objects = [SceneJsonLoader._parse_object(o, materials) for o in root["objects"]]

        return scene
