"""Renderizador OpenGL 3.3: passe da luz + passe da câmera (seção 6.9)."""

import ctypes
from pathlib import Path

import numpy as np
import pygame
from OpenGL import GL as gl
from OpenGL.GL.shaders import compileProgram, compileShader

from framework import matrix as mat

ROOT = Path(__file__).resolve().parents[1]

# Os principais programas utilizados são:
#lit.vert: processamento dos vértices.
#lit.frag: cálculo da aparência dos pixels, incluindo iluminação.
#depth.vert e depth.frag: geração das informações de profundidade utilizadas nas sombras.

class Program: # Representa um programa GLSL compilado
    def __init__(self, name):
        vertex = (ROOT / "shaders" / f"{name}.vert").read_text(encoding="utf-8")
        fragment = (ROOT / "shaders" / f"{name}.frag").read_text(encoding="utf-8")
        self.id = compileProgram(
            compileShader(vertex, gl.GL_VERTEX_SHADER),
            compileShader(fragment, gl.GL_FRAGMENT_SHADER),
        )
        self.locations = {}

    def use(self): #Ativa o programa
        gl.glUseProgram(self.id)

    def location(self, name): # Busca e cacheia a localização de um uniforme
        if name not in self.locations:
            self.locations[name] = gl.glGetUniformLocation(self.id, name)
        return self.locations[name]

    def matrix(self, name, value): # Garante um array contiguo
        value = np.ascontiguousarray(value, dtype=np.float32)
        fn = gl.glUniformMatrix3fv if value.shape == (3, 3) else gl.glUniformMatrix4fv
        fn(self.location(name), 1, gl.GL_TRUE, value)

    def vector(self, name, value): # Envia um uniform para vec2 ou vec3
        fn = gl.glUniform2f if len(value) == 2 else gl.glUniform3f
        fn(self.location(name), *map(float, value))

    def integer(self, name, value): #Booleanos ou samplers
        gl.glUniform1i(self.location(name), int(value))

    def scalar(self, name, value): # float para escalares
        gl.glUniform1f(self.location(name), float(value))


class Shadow:
    def __init__(self, resolution=2048):
        self.resolution = resolution
        self.direction = mat.normalized((-0.6, -1.0, -0.45)) # direção de propagação
        target = np.array([0, 1, 0], dtype=np.float32) # origem da luz
        self.matrix = mat.orthographic(-15, 15, -15, 15, 1, 55) @ mat.look_at(
            target - self.direction * 26, target
        )
        self.texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_DEPTH_COMPONENT24,
            resolution,
            resolution,
            0,
            gl.GL_DEPTH_COMPONENT,
            gl.GL_FLOAT,
            None,
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST) # não é necessário interpolar profundidade
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_BORDER) # fora do mapa o fragmento é considerado iluminado 
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_BORDER)
        gl.glTexParameterfv(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_BORDER_COLOR, np.ones(4, dtype=np.float32)
        )
        self.fbo = gl.glGenFramebuffers(1) # FrameBuffer
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_TEXTURE_2D, self.texture, 0
        )
        gl.glDrawBuffer(gl.GL_NONE)
        gl.glReadBuffer(gl.GL_NONE)
        if gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER) != gl.GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Framebuffer de sombras incompleto.")
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)


class Renderer:
    def __init__(self, shadow_resolution=2048):
        self.lit = Program("lit")
        self.depth = Program("depth")
        self.overlay = Program("overlay")
        self.shadow = Shadow(shadow_resolution)
        self.geometry_cache = {}
        self.textures = {}
        self.overlay_texture = gl.glGenTextures(1)
        self.overlay_vao = gl.glGenVertexArrays(1)
        self.overlay_size = None
        self.shadows_enabled = True
        self.procedural_enabled = True
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_CULL_FACE)
        gl.glCullFace(gl.GL_BACK)
        gl.glClearColor(0.055, 0.09, 0.13, 1)

    def geometry(self, geometry): # Crie e cacheia um VAO e um VBO para geometria
        if geometry not in self.geometry_cache:
            vao, vbo = gl.glGenVertexArrays(1), gl.glGenBuffers(1)
            gl.glBindVertexArray(vao)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
            data = geometry.vertices
            gl.glBufferData(gl.GL_ARRAY_BUFFER, data.nbytes, data, gl.GL_STATIC_DRAW)
            for location, size, offset in ((0, 3, 0), (1, 3, 12), (2, 2, 24)):
                gl.glEnableVertexAttribArray(location)
                gl.glVertexAttribPointer(
                    location, size, gl.GL_FLOAT, False, 32, ctypes.c_void_p(offset)
                )
            self.geometry_cache[geometry] = (vao, vbo, len(data))
        return self.geometry_cache[geometry]

    def texture(self, path): # Carrega a imagem PNG e envia para a GPU
        if path not in self.textures:
            surface = pygame.image.load(str(ROOT / path))
            pixels = pygame.image.tobytes(surface, "RGBA", True)
            texture = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
            gl.glTexImage2D(
                gl.GL_TEXTURE_2D,
                0,
                gl.GL_RGBA8,
                *surface.get_size(),
                0,
                gl.GL_RGBA,
                gl.GL_UNSIGNED_BYTE,
                pixels,
            )
            gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
            gl.glTexParameteri(
                gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR
            )
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            self.textures[path] = texture
        return self.textures[path]

    def draw(self, mesh): # Desenha a geometria da malha como triângulos (os vértices já estão na ordem)
        vao, _, count = self.geometry(mesh.geometry)
        gl.glBindVertexArray(vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, count)

    def render(self, scene, camera, size): # Recebe o grafo, camera e tamanho da janela
        width, height = size # Preparação
        meshes = list(scene.meshes())
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_CULL_FACE)
        if self.shadows_enabled: # Passe de sombra
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.shadow.fbo)
            gl.glViewport(0, 0, self.shadow.resolution, self.shadow.resolution)
            gl.glClear(gl.GL_DEPTH_BUFFER_BIT)
            self.depth.use()
            self.depth.matrix("lightMatrix", self.shadow.matrix)
            for mesh, world in meshes:
                if mesh.cast_shadow:
                    self.depth.matrix("modelMatrix", world)
                    self.draw(mesh)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0) # Retorno para a camera principal
        gl.glViewport(0, 0, width, height)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        self.lit.use() # Uniforms globais
        self.lit.matrix("viewMatrix", camera.view_matrix())
        self.lit.matrix("projectionMatrix", camera.projection_matrix(width / height))
        self.lit.matrix("lightMatrix", self.shadow.matrix)
        self.lit.vector("lightDirection", self.shadow.direction)
        self.lit.vector("cameraPosition", camera.eye)
        self.lit.integer("shadowsEnabled", self.shadows_enabled)
        self.lit.integer("shadowMap", 1)
        self.lit.integer("colorTexture", 0)
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.shadow.texture)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        for mesh, world in meshes: # Desenho de cada malha
            material = mesh.material
            self.lit.matrix("modelMatrix", world)
            self.lit.matrix("normalMatrix", np.linalg.inv(world[:3, :3]).T)
            self.lit.vector("baseColor", material.color)
            self.lit.vector("uvRepeat", material.uv_repeat)
            self.lit.scalar("specularStrength", material.specular)
            self.lit.scalar("shininess", material.shininess)
            self.lit.scalar("emission", material.emission)
            self.lit.integer("proceduralEnabled", material.procedural and self.procedural_enabled)
            self.lit.integer("useTexture", material.texture is not None)
            gl.glBindTexture(
                gl.GL_TEXTURE_2D, self.texture(material.texture) if material.texture else 0
            )
            self.draw(mesh)
        gl.glBindVertexArray(0)

    def draw_overlay(self, surface): # Desenha o HUD por cima da cena
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.overlay_texture)
        pixels = pygame.image.tobytes(surface, "RGBA", True)
        size = surface.get_size()
        if self.overlay_size != size:
            gl.glTexImage2D(
                gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, *size, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, pixels
            )
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            self.overlay_size = size
        else:
            gl.glTexSubImage2D(
                gl.GL_TEXTURE_2D, 0, 0, 0, *size, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, pixels
            )
        self.overlay.use()
        self.overlay.integer("overlayTexture", 0)
        gl.glBindVertexArray(self.overlay_vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)
        gl.glBindVertexArray(0)
        gl.glDisable(gl.GL_BLEND)

    def save_frame(self, path, size):
        """Lê o back buffer antes do swap, inclusive no modo offscreen."""
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
        data = gl.glReadPixels(0, 0, *size, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
        surface = pygame.image.frombytes(data, size, "RGB", True)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(path))

    def close(self): # Libera os recursos da GPU
        for vao, vbo, _ in self.geometry_cache.values():
            gl.glDeleteVertexArrays(1, [vao])
            gl.glDeleteBuffers(1, [vbo])
        gl.glDeleteVertexArrays(1, [self.overlay_vao])
        gl.glDeleteTextures([*self.textures.values(), self.overlay_texture, self.shadow.texture])
        gl.glDeleteFramebuffers(1, [self.shadow.fbo])
        for program in (self.lit, self.depth, self.overlay):
            gl.glDeleteProgram(program.id)
