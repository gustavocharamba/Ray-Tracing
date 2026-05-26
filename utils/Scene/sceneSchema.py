from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from src.Ponto import Ponto
from src.Vetor import Vetor


@dataclass
class ColorData:
    r: float = 0.0
    g: float = 0.0
    b: float = 0.0

    def __repr__(self):
        return f"[{self.r}, {self.g}, {self.b}]"


@dataclass
class CameraData:
    lookfrom:        Ponto = field(default_factory=lambda: Ponto(0, 0, 0))
    lookat:          Ponto = field(default_factory=lambda: Ponto(0, 0, -1))
    up_vector:       Vetor = field(default_factory=lambda: Vetor(0, 1, 0))
    image_width:     int   = 800
    image_height:    int   = 800
    screen_distance: float = 1.0


@dataclass
class TransformData:
    t_type: str   = ""  # "translation" | "scaling" | "rotation"
    data:   Vetor = field(default_factory=lambda: Vetor(0, 0, 0))


@dataclass
class MaterialData:
    name:  str       = ""
    color: ColorData = field(default_factory=ColorData)  # kd (difuso)
    ks:    ColorData = field(default_factory=ColorData)  # especular
    ka:    ColorData = field(default_factory=ColorData)  # ambiente
    kr:    ColorData = field(default_factory=ColorData)  # reflexivo
    kt:    ColorData = field(default_factory=ColorData)  # transmissivo
    ns:    float     = 1.0   # rugosidade / brilho
    ni:    float     = 1.0   # índice de refração
    d:     float     = 1.0   # opacidade


@dataclass
class LightData:
    pos:        Ponto          = field(default_factory=lambda: Ponto(0, 0, 0))
    color:      ColorData      = field(default_factory=ColorData)
    extra_data: Dict[str, str] = field(default_factory=dict)


@dataclass
class ObjectData:
    obj_type:         str                 = ""
    relative_pos:     Ponto               = field(default_factory=lambda: Ponto(0, 0, 0))
    material:         MaterialData        = field(default_factory=MaterialData)
    numeric_data:     Dict[str, float]    = field(default_factory=dict)
    vetor_point_data: Dict[str, Vetor]    = field(default_factory=dict)
    other_properties: Dict[str, str]      = field(default_factory=dict)
    transforms:       List[TransformData] = field(default_factory=list)

    def get_num(self, key: str) -> float:
        return self.numeric_data[key]

    def get_int(self, key: str) -> int:
        return int(self.numeric_data[key])

    def get_vetor(self, key: str) -> Vetor:
        return self.vetor_point_data[key]

    def get_ponto(self, key: str) -> Ponto:
        v = self.vetor_point_data[key]
        return Ponto(v.x, v.y, v.z)

    def get_property(self, key: str) -> str:
        return self.other_properties[key]


@dataclass
class SceneData:
    camera:       CameraData      = field(default_factory=CameraData)
    global_light: LightData       = field(default_factory=LightData)
    light_list:   List[LightData] = field(default_factory=list)
    objects:      List[ObjectData] = field(default_factory=list)
