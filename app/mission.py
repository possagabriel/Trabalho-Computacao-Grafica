"""Linha do tempo por etapas: dependências explícitas e poses determinísticas.

Sem OpenGL: o controlador pode ser testado sem abrir uma janela.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Stage: # Representa uma etapa da missão, é imutável
    name: str
    duration: float
    description: str


STAGES = ( # Tupla com as 9 etapas da missão
    Stage("Preparação", 2, "A base autoriza a missão. As duas aeronaves aguardam nos helipontos."),
    Stage("Decolagem", 4, "O helicóptero sobe; o drone aguarda a chegada ao ponto de encontro."),
    Stage(
        "Aproximação", 5, "O helicóptero alcança o ponto de encontro e libera a decolagem do drone."
    ),
    Stage(
        "Encontro",
        3,
        "O drone decola e se posiciona ao lado do helicóptero, que permanece em espera.",
    ),
    Stage(
        "Inspeção", 6, "O drone contorna o helicóptero. A partida depende do fim desta inspeção."
    ),
    Stage("Escolta", 6, "Inspeção concluída: o helicóptero parte e o drone mantém a formação."),
    Stage("Retorno", 5, "O fim da escolta inicia o retorno coordenado aos dois helipontos."),
    Stage("Pouso", 4, "As duas aeronaves descem aos respectivos helipontos."),
    Stage("Conclusão", 2, "Missão concluída. A base prepara o próximo ciclo."),
)
CYCLE_DURATION = sum(stage.duration for stage in STAGES) # Define a duração total do ciclo, 37
HELI_PAD = (-3.2, 0.16, 0.5) # Heliponto do helicóptero
DRONE_PAD = (3.8, 0.16, 3.0) # Heliponto do drone
HELI_AIR = (-3.2, 3.5, 0.5) # Ponto de subida do helicóptero
MEETING = (1.1, 3.5, -0.5) # Ponto de encontro
DESTINATION = (-1.6, 4.5, -3.8) # Destino da escolta
OFFSET = (2.8, 0.35, 1.7) # Deslocamento do drone em relação ao helicóptero
DRONE_AIR = (3.8, 2.6, 3.0) # Ponto aéreo do drone no retorno

# Calcula a posição intermediária entre dois pontos
def add(a, b): # Soma dois vetores, representados por tuplas
    return tuple(x + y for x, y in zip(a, b)) # Usado para MEETING + OFFSET e DESTINATION + OFFSET


def smoothstep(t): # Suaviza o movimento fazendo com que a aeronave acelere e desacelere gradualmente.
    return t * t * (3 - 2 * t)


def lerp(a, b, t): # Interpolação linear entre dois pontos
    s = smoothstep(t)
    return tuple(x + (y - x) * s for x, y in zip(a, b))


def angle_lerp(a, b, t): # Interpolação angular pelo caminho mais curto
    delta = (b - a + math.pi) % math.tau - math.pi # Calcula a diferença para o intervalo [-π, π], evita que o heli vire pelo lado errado
    return a + delta * smoothstep(t)


@dataclass(frozen=True)
class Pose: # Retrato imutável do estado das aeronaves em um instante
    stage_index: int
    progress: float
    helicopter: tuple
    drone: tuple
    helicopter_yaw: float
    drone_yaw: float
    cycle: int
    helicopter_pitch: float = 0.0
    helicopter_roll: float = 0.0
    drone_pitch: float = 0.0
    drone_roll: float = 0.0


def rotor_motion(time, drone=False): # Calcula a fase dos rotores e a potencia atual
    """Integral exata da velocidade de partida/parada, independente do FPS.

    Retorna (tempo angular equivalente em velocidade plena, potência de 0 a 1).
    A fase acumulada atravessa os ciclos sem saltos na orientação das pás.
    """
    cycle, t = divmod(time, CYCLE_DURATION)
    start, stop, ramp = (9.0 if drone else 0.0), 35.0, 2.0
    area_per_cycle = stop - start

    def integral(u): # Integral exata do smoothstep(u) = 3u² − 2u³ o que permite calcular a fase diretamente
        return u**3 - 0.5 * u**4

    if t < start: # Antes da partida 
        area, power = 0.0, 0.0
    elif t < start + ramp: # Durante a rampa da partida
        u = (t - start) / ramp
        area, power = ramp * integral(u), smoothstep(u)
    elif t < stop: # Velocidade plena
        area, power = t - start - ramp / 2, 1.0
    else: # Durante a parada
        u = (t - stop) / ramp
        area = stop - start - ramp / 2 + ramp * (u - integral(u))
        power = 1 - smoothstep(u)
    return cycle * area_per_cycle + area, power


def flight_tilt(velocity, yaw): # Calcula inclinações a partir da velocidade
    """Inclinação ilustrativa em relação ao deslocamento no referencial da aeronave."""
    vx, _, vz = velocity
    forward = vx * math.sin(yaw) + vz * math.cos(yaw)
    sideways = vx * math.cos(yaw) - vz * math.sin(yaw)
    return (max(-0.16, min(0.16, forward * 0.09)), max(-0.18, min(0.18, -sideways * 0.12)))


def sample(time): # Função principal, recebe segundos e devolve uma pose
    """A pose depende de segundos transcorridos, nunca do número de frames."""
    if not math.isfinite(time) or time < 0: # Validação
        raise ValueError("Tempo deve ser finito e não negativo.")
    remaining = time % CYCLE_DURATION
    index = 0
    for index, stage in enumerate(STAGES): # Descoberta da etapa
        if remaining < stage.duration:
            break
        remaining -= stage.duration
    p = remaining / STAGES[index].duration
    near = add(MEETING, OFFSET) # Pontos auxiliares da escolta
    far = add(DESTINATION, OFFSET)
    heli_paths = [ # Caminhos do helicóptero
        (HELI_PAD, HELI_PAD), # Preparação
        (HELI_PAD, HELI_AIR), # Decolagem
        (HELI_AIR, MEETING), # Aproximação
        (MEETING, MEETING), # Encontro: espera
        (MEETING, MEETING), # Inspeção: espera
        (MEETING, DESTINATION), # Escolta
        (DESTINATION, HELI_AIR), # Retorno
        (HELI_AIR, HELI_PAD), # Pouso
        (HELI_PAD, HELI_PAD), # Conclusão
    ]
    drone_paths = [(DRONE_PAD, DRONE_PAD)] * 3 + [ # Caminhos do drone
        (DRONE_PAD, near), # Encontro: decola e vai ao lado do helicóptero
        (near, near), # Inspeção: base para o movimento circular
        (near, far), # Escolta
        (far, DRONE_AIR), # Retorno
        (DRONE_AIR, DRONE_PAD), # Pouso
        (DRONE_PAD, DRONE_PAD), # Conclusão
    ]
    helicopter = lerp(*heli_paths[index], p)
    drone = lerp(*drone_paths[index], p)
    derivative = 6 * p * (1 - p) / STAGES[index].duration # É a derivada de smoothstep em relação ao tempo
    heli_velocity = tuple((b - a) * derivative for a, b in zip(*heli_paths[index]))
    drone_velocity = tuple((b - a) * derivative for a, b in zip(*drone_paths[index]))
    if index == 4:
        # Começa e termina exatamente no mesmo deslocamento da escolta.
        a = math.atan2(OFFSET[2], OFFSET[0]) + math.tau * smoothstep(p) # Em vez de interpolar near -> near
        radius = math.hypot(OFFSET[0], OFFSET[2])
        drone = add(helicopter, (radius * math.cos(a), OFFSET[1], radius * math.sin(a)))
        omega = math.tau * derivative 
        drone_velocity = (-radius * math.sin(a) * omega, 0, radius * math.cos(a) * omega) # Velocidade é calculada pela derivada do movimento circular
    headings = [ # Yam do helicoptero
        (0, 0),
        (0, math.pi / 2),
        (math.pi / 2, math.pi / 2),
        (math.pi / 2, math.pi / 2),
        (math.pi / 2, -2.45),
        (-2.45, -2.45),
        (-2.45, 0),
        (0, 0),
        (0, 0),
    ]
    heli_yaw = angle_lerp(*headings[index], p)
    # A câmera do drone olha para o helicóptero durante reconhecimento/escolta.
    dx, dz = helicopter[0] - drone[0], helicopter[2] - drone[2] # Yam do drone
    drone_yaw = math.atan2(dx, dz)
    return Pose( # Retorno das poses
        index,
        p,
        helicopter,
        drone,
        heli_yaw,
        drone_yaw,
        int(time // CYCLE_DURATION),
        *flight_tilt(heli_velocity, heli_yaw),
        *flight_tilt(drone_velocity, drone_yaw),
    )


class Mission: # Estado mutável da aplicação
    def __init__(self):
        self.time = 0.0
        self.paused = False
        self.speed = 1.0

    @property
    def pose(self): # Só chama sample (114)
        return sample(self.time)

    def advance(self, dt): # Avança o tempo
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("Delta de tempo deve ser finito e não negativo.")
        if not self.paused:
            self.time += dt * self.speed

    def reset(self): # Volta o tempo para zero
        self.time = 0.0

    def next_stage(self): 
        """Atalho didático: salta para o início da próxima etapa."""
        pose = self.pose
        start = sum(s.duration for s in STAGES[: pose.stage_index + 1])
        self.time = pose.cycle * CYCLE_DURATION + start # Se estiver na última etapa vira 37

    def seek(self, stage_index, progress=0.0):
        """Navegação da linha do tempo, preservando ciclo, velocidade e pausa."""
        if not 0 <= stage_index < len(STAGES) or not 0 <= progress <= 1:
            raise ValueError("Etapa ou progresso fora do intervalo.")
        start = sum(stage.duration for stage in STAGES[:stage_index])
        self.time = (
            self.pose.cycle * CYCLE_DURATION + start + STAGES[stage_index].duration * progress
        )
