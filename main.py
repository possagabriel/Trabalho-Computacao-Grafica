"""Aplicação Python/Pygame/OpenGL — execute: python main.py."""

import argparse
import math
import os
import sys
import time
from pathlib import Path


def arguments(): # Configura e valida os argumentos de linha de comando
    parser = argparse.ArgumentParser(
        description="Base Aurora — drone e helicóptero em missão coordenada."
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Usar SDL offscreen (teste sem janela; requer suporte do driver).",
    )
    parser.add_argument(
        "--frames", type=int, default=0, help="Encerrar após N quadros; 0 = execução interativa."
    )
    parser.add_argument(
        "--time", type=float, default=0, help="Instante inicial da missão, em segundos."
    )
    parser.add_argument(
        "--fixed-dt", type=float, default=None, help="Passo temporal fixo para testes/reprodução."
    )
    parser.add_argument("--screenshot", type=Path, help="Salvar último quadro em PNG.")
    parser.add_argument(
        "--size", type=int, nargs=2, default=(1280, 800), metavar=("LARGURA", "ALTURA")
    )
    parser.add_argument("--shadow-size", type=int, choices=(512, 1024, 2048, 4096), default=2048)
    parser.add_argument(
        "--msaa",
        type=int,
        choices=(0, 2, 4, 8),
        default=4,
        help="Amostras de antisserrilhamento; 0 desativa. Fallback automático.",
    )
    parser.add_argument(
        "--view",
        choices=("base", "encontro", "topo"),
        default="base",
        help="Enquadramento inicial da câmera.",
    )
    parser.add_argument("--no-ui", action="store_true", help="Ocultar o painel para capturas.")
    parser.add_argument(
        "--no-shadows", action="store_true", help="Desligar sombras para comparação didática."
    )
    args = parser.parse_args() # Validações
    if args.frames < 0 or min(args.size) < 480: # Dimensões mínimas
        parser.error("frames deve ser não negativo e as dimensões devem ser pelo menos 480.")
    if not math.isfinite(args.time) or args.time < 0: # Tempo finito, não negativo
        parser.error("time deve ser finito e não negativo.")
    if args.fixed_dt is not None and (not math.isfinite(args.fixed_dt) or args.fixed_dt < 0): # fixed-dt válido
        parser.error("fixed-dt deve ser finito e não negativo.")
    if args.headless and not args.frames: # ajuste automático de frames para headless/screenshot
        args.frames = 1
    if args.screenshot and not args.frames:
        args.frames = 1
    return args


def run(args): # Variáveis do Pygame e SDL offscreen
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "offscreen"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame # Import de Pygame, OpenGL, HUD, Mission, Scene, Camera, Renderer e janela
    from OpenGL import GL as gl

    from app.hud import HUD
    from app.mission import Mission
    from app.scene import apply_mission, build_scene
    from framework.core import Camera
    from framework.renderer import Renderer
    from framework.window import create_window

    pygame.display.init() # plica MSAA, cria o Renderer e a cena
    pygame.font.init()
    renderer = None
    try:
        samples = create_window(args.size, args.msaa)
        pygame.display.set_caption("Base Aurora | Drone + Helicóptero | Computação Gráfica")
        print("OpenGL:", gl.glGetString(gl.GL_VERSION).decode())
        print("Renderizador:", gl.glGetString(gl.GL_RENDERER).decode())
        print("Antisserrilhamento MSAA:", samples)
        print("Espaço: pausar | Setas: câmera | WASD: mover | Q/E: zoom | H: ajuda | Esc: sair")
        renderer = Renderer(args.shadow_size)
        renderer.shadows_enabled = not args.no_shadows
        scene, helicopter, drone = build_scene() # Instancia estados 
        camera, mission, hud = Camera(), Mission(), HUD()

        def preset(view): # função interna que reposiciona a câmera para as posições base, encontro e topo
            camera.reset()
            if view == "encontro":
                camera.target[:] = (1, 4.0, -0.5)
                camera.distance = 12
                camera.elevation = 0.27
            elif view == "topo":
                camera.elevation = 1.4
                camera.distance = 23

        preset(args.view)
        mission.time = args.time
        dragging, show_ui = False, not args.no_ui
        clock = pygame.time.Clock()
        last_time = time.perf_counter()
        frames, running = 0, True
        while running: # loop principal
            now = time.perf_counter()
            elapsed, last_time = now - last_time, now
            dt = args.fixed_dt if args.fixed_dt is not None else elapsed # mede dt
            capture = None
            for event in pygame.event.get(): # trata eventos de teclado e mouse
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    key = event.key
                    if key == pygame.K_ESCAPE:
                        running = False
                    elif key == pygame.K_SPACE:
                        mission.paused = not mission.paused
                    elif key == pygame.K_r:
                        mission.reset()
                    elif key == pygame.K_n:
                        mission.next_stage()
                    elif key == pygame.K_c:
                        camera.reset()
                    elif key == pygame.K_h:
                        hud.show_help = not hud.show_help
                    elif key == pygame.K_TAB:
                        show_ui = not show_ui
                    elif key == pygame.K_f:
                        camera.tracking = not camera.tracking
                    elif key == pygame.K_p:
                        renderer.shadows_enabled = not renderer.shadows_enabled
                    elif key == pygame.K_b:
                        renderer.procedural_enabled = not renderer.procedural_enabled
                    elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        mission.speed = min(4, mission.speed * 2)
                    elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        mission.speed = max(0.25, mission.speed / 2)
                    elif key == pygame.K_F12:
                        capture = Path("captures") / time.strftime("aurora-%Y%m%d-%H%M%S.png")
                    elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        preset(
                            {pygame.K_1: "base", pygame.K_2: "encontro", pygame.K_3: "topo"}[key]
                        )
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    dragging = not (show_ui and hud.handle_click(event.pos, mission, camera))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging = False
                elif event.type == pygame.WINDOWFOCUSLOST:
                    dragging = False
                elif event.type == pygame.MOUSEMOTION and dragging:
                    camera.drag(*event.rel)
                elif event.type == pygame.MOUSEWHEEL:
                    camera.distance = max(6, min(40, camera.distance - event.y))
            if not running:
                break
            keys = pygame.key.get_pressed()
            camera.control(
                int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT]),
                int(keys[pygame.K_UP]) - int(keys[pygame.K_DOWN]),
                int(keys[pygame.K_q]) - int(keys[pygame.K_e]),
                int(keys[pygame.K_d]) - int(keys[pygame.K_a]),
                int(keys[pygame.K_w]) - int(keys[pygame.K_s]),
                min(elapsed, 0.1),
            )
            # O primeiro quadro mostra exatamente --time; depois soma dt em segundos.
            if frames:
                mission.advance(dt) # Atualiza a missão
            apply_mission(mission, helicopter, drone) # Aplica as poses
            camera.follow(helicopter.position, drone.position, min(elapsed, 0.1)) # Atualiza a câmera
            size = pygame.display.get_window_size() 
            if min(size) <= 0:
                clock.tick(30)
                continue
            renderer.render(scene, camera, size) # Renderiza a cena
            if show_ui: # Mostra o HUD
                hud.tracking = camera.tracking
                renderer.draw_overlay(hud.draw(size, mission, renderer, clock.get_fps()))
            frames += 1
            is_last = args.frames and frames >= args.frames
            if args.screenshot and is_last:
                capture = args.screenshot
            if capture:
                renderer.save_frame(capture, size)
                print("Captura salva:", capture)
            pygame.display.flip()
            if is_last:
                running = False
            if not args.headless:
                clock.tick(60)
        error = gl.glGetError() # Verifica erros OpenGL, fecha  renderer e encerra o Pygame
        if error != gl.GL_NO_ERROR:
            raise RuntimeError(f"Erro OpenGL ao finalizar: {error}")
        return 0
    finally:
        if renderer is not None:
            renderer.close()
        pygame.quit()


if __name__ == "__main__": # Inicializa a aplicação, trata erros de import e outras exceções
    try:
        raise SystemExit(run(arguments()))
    except ImportError as error:
        print(
            f"Dependência ausente: {error}. Execute: python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(1)
    except Exception as error:
        print(f"Não foi possível executar a cena: {error}", file=sys.stderr)
        print(
            "Verifique o suporte a OpenGL 3.3 e consulte README.md para diagnóstico.",
            file=sys.stderr,
        )
        raise SystemExit(1)
