"""Grafo de cena: Object3D → Scene/Camera/Mesh; Geometry + Material."""

import math
from dataclasses import dataclass

import numpy as np

from framework import matrix as mat


class Object3D: # Tudo que pode ser colocado na cena
    def __init__(self, name="objeto"):
        self.name = name # arrays NumPy, mesmo tipo esperado pelas matrizes e shaders
        self.position = np.zeros(3, dtype=np.float32)
        self.rotation = np.zeros(3, dtype=np.float32)
        self.scaling = np.ones(3, dtype=np.float32)
        self.parent = None
        self.children = []
        self.visible = True

    def add(self, child): # Adiciona um filho
        ancestor = self
        while ancestor is not None: # verifica por ciclos
            if ancestor is child:
                raise ValueError("O grafo não pode conter ciclos.")
            ancestor = ancestor.parent
        if child.parent is not None: # se o filho já tinha pai, é removido do pai antigo
            child.parent.children.remove(child)
        child.parent = self
        self.children.append(child)
        return child

    # Calcula a matriz de transformação local do objeto.
    def local_matrix(self): # M = T × Ry × Rx × Rz × S, matrizes são aplicadas da direita para esquerda (p → S → Rz → Rx → Ry → T)
        x, y, z = self.rotation
        return (
            mat.translation(*self.position) # translação 
            @ mat.rotation_y(y) # rotação em y
            @ mat.rotation_x(x) # rotação em x
            @ mat.rotation_z(z) # rotação em z
            @ mat.scale(*self.scaling) # escala
        )

    # Calcula sua transformação considerando também os objetos pais.
    def world_matrix(self): # É o produto da matriz do pai local
        local = self.local_matrix()
        return local if self.parent is None else self.parent.world_matrix() @ local

    def meshes(self, parent_matrix=None): # método que o renderer usa para percorrer a árvore de nós
        if not self.visible: # Se visible igual a False, nó e filhos não são desenhados
            return
        world = self.local_matrix()
        if parent_matrix is not None:
            world = parent_matrix @ world
        if isinstance(self, Mesh):
            yield self, world
        for child in self.children:
            yield from child.meshes(world)


class Scene(Object3D): # Subclase de Object3d, usada como raiz, não adiciona comportamento.
    pass               # Serve para indicar que aquele nó representa a cena inteira


@dataclass(frozen=True)
class Material: # Descreve as propriedades visuais, é imutável 
    color: tuple = (1, 1, 1)
    texture: str | None = None
    uv_repeat: tuple = (1, 1)
    specular: float = 0.25
    shininess: float = 32.0
    emission: float = 0.0
    procedural: bool = False 
    #Renderer traduz esses campos em uniforms.


class Mesh(Object3D): # É um Obect3d que contém geometry, material e cast_shadow
    def __init__(self, geometry, material, name="malha", cast_shadow=True):
        super().__init__(name)
        self.geometry = geometry
        self.material = material
        self.cast_shadow = cast_shadow


class Camera(Object3D): # Herda de Object3d, mas não utiliza position, para se posicionar diretamente
    """Câmera orbital em perspectiva com alvo deslocável pelo teclado."""

    def __init__(self):
        super().__init__("camera")
        self.reset()

    def reset(self):
        self.target = np.array([0, 0.2, 0], dtype=np.float32)
        self.azimuth = math.radians(34)
        self.elevation = math.radians(32)
        self.distance = 24.0
        self.tracking = False

    @property
    def eye(self): # posição da câmera no mundo
        c = math.cos(self.elevation)
        return self.target + self.distance * np.array(
            [c * math.sin(self.azimuth), math.sin(self.elevation), c * math.cos(self.azimuth)],
            dtype=np.float32,
        )

    def view_matrix(self): # Constroi a matriz de visão, do olho para o alvo
        return mat.look_at(self.eye, self.target)

    def projection_matrix(self, aspect): # Perspectiva de 48º
        return mat.perspective(math.radians(48), aspect, 0.1, 100.0)

    def control(self, orbit_x, orbit_y, zoom, pan_x, pan_z, dt): # Atualiza a câmera com base nas teclas presionadas
        self.azimuth += orbit_x * dt # vem das setas
        self.elevation = np.clip(self.elevation + orbit_y * dt, 0.12, 1.45) # limitado entre 7 e 83
        self.distance = np.clip(self.distance + zoom * dt * 9, 6, 40) # limite entre 6 e 40
        right = np.array([math.cos(self.azimuth), 0, -math.sin(self.azimuth)])
        forward = np.array([-math.sin(self.azimuth), 0, -math.cos(self.azimuth)])
        self.target += (right * pan_x + forward * pan_z) * dt * 5
        self.target[[0, 2]] = np.clip(self.target[[0, 2]], -12, 12)
        if pan_x or pan_z:
            self.tracking = False

    def drag(self, dx, dy): # Arrasto do mouse 
        self.azimuth -= dx * 0.006 # Sensibilidade
        self.elevation = float(np.clip(self.elevation + dy * 0.006, 0.12, 1.45))

    def follow(self, helicopter, drone, dt): # O alvo é o ponto médio entre a helicóptero e o drone
        if self.tracking:
            target = (np.asarray(helicopter) + np.asarray(drone)) * 0.5 + (0, 0.8, 0) # +0,8 para melhor enquadramento
            self.target += (target - self.target) * (1 - math.exp(-4 * dt))
