import pygame
import asyncio
import platform
import numpy as np

WIDTH = 800
HEIGHT = 600
FPS = 15
RENDER_WIDTH = 400
RENDER_HEIGHT = 300
PREVIEW_WIDTH = 160
PREVIEW_HEIGHT = 120
BASE_ITER = 150
MAX_ITER_CAP = 1000
ZOOM = 150.0
INITIAL_ZOOM = 150.0
OFFSET_X = -2.0
OFFSET_Y = -1.5
ZOOM_FACTOR = 1.5
PAN_SMOOTH = 0.8
PAN_STEP = 50.0
INITIAL_OFFSET_X = -2.0
INITIAL_OFFSET_Y = -1.5

def get_max_iter(zoom):
    return min(BASE_ITER + int(50 * max(0, np.log10(zoom / INITIAL_ZOOM))), MAX_ITER_CAP)

def mandelbrot(height, width, offset_x, offset_y, zoom, max_iter):
    x = np.linspace(offset_x, offset_x + width / zoom, width)
    y = np.linspace(offset_y, offset_y + height / zoom, height)
    X, Y = np.meshgrid(x, y)
    c = X + 1j * Y
    z = np.zeros_like(c, dtype=np.complex128)
    output = np.zeros(c.shape, dtype=np.int32)
    for i in range(max_iter):
        mask = np.abs(z) <= 2
        z[mask] = z[mask] * z[mask] + c[mask]
        output += mask
    escaped = output < max_iter
    smooth = np.zeros_like(output, dtype=np.float64)
    smooth[escaped] = output[escaped] + 1 - np.log(np.log(np.abs(z[escaped])) / np.log(2)) / np.log(2)
    return smooth

def setup():
    global screen, font, render_surface, preview_surface
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Mandelbrot Fractal")
    font = pygame.font.SysFont("arial", 20)
    render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))
    preview_surface = pygame.Surface((PREVIEW_WIDTH, PREVIEW_HEIGHT))
    draw_mandelbrot(True)

def draw_mandelbrot(full_resolution):
    global surface
    width = RENDER_WIDTH if full_resolution else PREVIEW_WIDTH
    height = RENDER_HEIGHT if full_resolution else PREVIEW_HEIGHT
    max_iter = get_max_iter(ZOOM)
    print(f"[render] {'full' if full_resolution else 'preview'} start | zoom={ZOOM:.3f} iter={max_iter} offset=({OFFSET_X:.6f},{OFFSET_Y:.6f})")
    output = mandelbrot(height, width, OFFSET_X, OFFSET_Y, ZOOM, max_iter)
    colors = np.zeros((height, width, 3), dtype=np.uint8)
    mask = output > 0
    t = output[mask] / max_iter
    colors[mask, 0] = (255 * t).astype(np.uint8)
    colors[mask, 1] = (255 * t).astype(np.uint8)
    colors[mask, 2] = (255 * (1 - t)).astype(np.uint8)
    target_surface = render_surface if full_resolution else preview_surface
    target_surface = pygame.surfarray.make_surface(colors)
    surface = pygame.transform.scale(target_surface, (WIDTH - 30, HEIGHT - 30))
    screen.fill((50, 50, 50))
    screen.blit(surface, (15, 15))
    rendering_text = font.render("Rendering...", True, (255, 255, 255))
    rendering_shadow = font.render("Rendering...", True, (0, 0, 0))
    screen.blit(rendering_shadow, (WIDTH - 129, 16))
    screen.blit(rendering_text, (WIDTH - 130, 15))
    pygame.display.flip()
    print(f"[render] {'full' if full_resolution else 'preview'} done")

async def main():
    global ZOOM, OFFSET_X, OFFSET_Y, surface
    setup()
    clock = pygame.time.Clock()
    running = True
    dragging = False
    dragged = False
    last_pos = None
    needs_full_render = False
    last_logged_fps_ms = 0
    last_zoom = ZOOM
    last_offset = (OFFSET_X, OFFSET_Y)
    print("[help] Controles: clique-esquerdo para zoom-in, clique-direito para zoom-out, arraste para mover, scroll para zoom, setas/WASD para pan, + e - para zoom, R para reset, H para ajuda.")
    while running:
        keys = pygame.key.get_pressed()
        pan_delta_x = 0
        pan_delta_y = 0
        if keys[pygame.K_LEFT]:
            pan_delta_x += PAN_STEP / ZOOM
        if keys[pygame.K_RIGHT]:
            pan_delta_x -= PAN_STEP / ZOOM
        if keys[pygame.K_UP]:
            pan_delta_y += PAN_STEP / ZOOM
        if keys[pygame.K_DOWN]:
            pan_delta_y -= PAN_STEP / ZOOM
        # WASD support
        if keys[pygame.K_a]:
            pan_delta_x += PAN_STEP / ZOOM
        if keys[pygame.K_d]:
            pan_delta_x -= PAN_STEP / ZOOM
        if keys[pygame.K_w]:
            pan_delta_y += PAN_STEP / ZOOM
        if keys[pygame.K_s]:
            pan_delta_y -= PAN_STEP / ZOOM
        if pan_delta_x != 0 or pan_delta_y != 0:
            OFFSET_X += pan_delta_x
            OFFSET_Y += pan_delta_y
            print(f"[move] pan dx={pan_delta_x:.6f} dy={pan_delta_y:.6f} -> offset=({OFFSET_X:.6f},{OFFSET_Y:.6f})")
            draw_mandelbrot(False)
            needs_full_render = True
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging = True
                    dragged = False
                    last_pos = event.pos
                elif event.button == 3:
                    mouse_x, mouse_y = event.pos
                    scaled_x = (mouse_x - 15) * RENDER_WIDTH // (WIDTH - 30)
                    scaled_y = (mouse_y - 15) * RENDER_HEIGHT // (HEIGHT - 30)
                    center_re = OFFSET_X + (scaled_x / ZOOM)
                    center_im = OFFSET_Y + (scaled_y / ZOOM)
                    ZOOM /= ZOOM_FACTOR
                    OFFSET_X = center_re - (scaled_x / ZOOM)
                    OFFSET_Y = center_im - (scaled_y / ZOOM)
                    print(f"[zoom] out @({scaled_x},{scaled_y}) -> zoom={ZOOM:.3f}")
                    draw_mandelbrot(False)
                    needs_full_render = True
            elif event.type == pygame.MOUSEWHEEL:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                scaled_x = (mouse_x - 15) * RENDER_WIDTH // (WIDTH - 30)
                scaled_y = (mouse_y - 15) * RENDER_HEIGHT // (HEIGHT - 30)
                center_re = OFFSET_X + (scaled_x / ZOOM)
                center_im = OFFSET_Y + (scaled_y / ZOOM)
                if event.y > 0:
                    ZOOM *= ZOOM_FACTOR
                    action = 'in'
                else:
                    ZOOM /= ZOOM_FACTOR
                    action = 'out'
                OFFSET_X = center_re - (scaled_x / ZOOM)
                OFFSET_Y = center_im - (scaled_y / ZOOM)
                print(f"[zoom] wheel {action} @({scaled_x},{scaled_y}) -> zoom={ZOOM:.3f}")
                draw_mandelbrot(False)
                needs_full_render = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False
                    if not dragged:
                        mouse_x, mouse_y = event.pos
                        scaled_x = (mouse_x - 15) * RENDER_WIDTH // (WIDTH - 30)
                        scaled_y = (mouse_y - 15) * RENDER_HEIGHT // (HEIGHT - 30)
                        center_re = OFFSET_X + (scaled_x / ZOOM)
                        center_im = OFFSET_Y + (scaled_y / ZOOM)
                        ZOOM *= ZOOM_FACTOR
                        OFFSET_X = center_re - (scaled_x / ZOOM)
                        OFFSET_Y = center_im - (scaled_y / ZOOM)
                        print(f"[zoom] in @({scaled_x},{scaled_y}) -> zoom={ZOOM:.3f}")
                        draw_mandelbrot(False)
                        needs_full_render = True
                    else:
                        needs_full_render = True
                    last_pos = None
            elif event.type == pygame.MOUSEMOTION and dragging:
                dragged = True
                mouse_x, mouse_y = event.pos
                dx = (mouse_x - last_pos[0]) * PAN_SMOOTH
                dy = (mouse_y - last_pos[1]) * PAN_SMOOTH
                OFFSET_X -= dx / ZOOM
                OFFSET_Y -= dy / ZOOM
                last_pos = (mouse_x, mouse_y)
                print(f"[move] drag dx={-dx/ZOOM:.6f} dy={-dy/ZOOM:.6f} -> offset=({OFFSET_X:.6f},{OFFSET_Y:.6f})")
                draw_mandelbrot(False)
                needs_full_render = True
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    center_re = OFFSET_X + (RENDER_WIDTH / 2) / ZOOM
                    center_im = OFFSET_Y + (RENDER_HEIGHT / 2) / ZOOM
                    ZOOM *= ZOOM_FACTOR
                    OFFSET_X = center_re - (RENDER_WIDTH / 2) / ZOOM
                    OFFSET_Y = center_im - (RENDER_HEIGHT / 2) / ZOOM
                    print(f"[zoom] in center -> zoom={ZOOM:.3f}")
                    draw_mandelbrot(False)
                    needs_full_render = True
                elif event.key == pygame.K_MINUS:
                    center_re = OFFSET_X + (RENDER_WIDTH / 2) / ZOOM
                    center_im = OFFSET_Y + (RENDER_HEIGHT / 2) / ZOOM
                    ZOOM /= ZOOM_FACTOR
                    OFFSET_X = center_re - (RENDER_WIDTH / 2) / ZOOM
                    OFFSET_Y = center_im - (RENDER_HEIGHT / 2) / ZOOM
                    print(f"[zoom] out center -> zoom={ZOOM:.3f}")
                    draw_mandelbrot(False)
                    needs_full_render = True
                elif event.key == pygame.K_r:
                    ZOOM = INITIAL_ZOOM
                    OFFSET_X = INITIAL_OFFSET_X
                    OFFSET_Y = INITIAL_OFFSET_Y
                    print(f"[reset] view reset -> zoom={ZOOM:.3f} offset=({OFFSET_X:.6f},{OFFSET_Y:.6f})")
                    draw_mandelbrot(False)
                    needs_full_render = True
                elif event.key == pygame.K_h:
                    print("[help] Controles: clique-esquerdo=zoom-in, clique-direito=zoom-out, scroll=zoom, arraste=pan, setas/WASD=pan, +=zoom-in, -=zoom-out, R=reset, H=ajuda")
        if needs_full_render and not (dragging or any(pygame.key.get_pressed()) or any(pygame.mouse.get_pressed())):
            draw_mandelbrot(True)
            needs_full_render = False
        screen.fill((50, 50, 50))
        screen.blit(surface, (15, 15))
        fps = str(int(clock.get_fps()))
        fps_text = font.render(f"FPS: {fps}", True, (255, 255, 255))
        fps_shadow = font.render(f"FPS: {fps}", True, (0, 0, 0))
        screen.blit(fps_shadow, (16, 16))
        screen.blit(fps_text, (15, 15))
        pygame.display.flip()
        clock.tick(FPS)
        # Log FPS once per second to avoid spam
        now_ms = pygame.time.get_ticks()
        if now_ms - last_logged_fps_ms >= 1000:
            print(f"[stats] fps={int(clock.get_fps())} zoom={ZOOM:.3f} offset=({OFFSET_X:.6f},{OFFSET_Y:.6f})")
            last_logged_fps_ms = now_ms
        # Log changes in zoom/offset
        if ZOOM != last_zoom:
            print(f"[state] zoom -> {ZOOM:.3f}")
            last_zoom = ZOOM
        if (OFFSET_X, OFFSET_Y) != last_offset:
            print(f"[state] offset -> ({OFFSET_X:.6f},{OFFSET_Y:.6f})")
            last_offset = (OFFSET_X, OFFSET_Y)
        await asyncio.sleep(1.0 / FPS)
    pygame.quit()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
