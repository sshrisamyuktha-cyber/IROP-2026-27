import csv
import datetime
import math
import os
import time
import pygame

WIDTH = 800
HEIGHT = 600
FPS = 60
SESSION_LENGTH = 30

ROAD_WIDTH = 220
ROAD_SPEED = 150

CAR_WIDTH = 36
CAR_HEIGHT = 55

GRASS = (40, 120, 60)
ROAD_COLOR = (60, 60, 60)
EDGE_COLOR = (235, 235, 235)
LINE_COLOR = (235, 210, 80)
CAR_COLOR = (220, 40, 40)


def road_center(y, road_progress):
    """Calculate the road centre at a given screen height."""
    distance = road_progress + y
    return (
        WIDTH / 2
        + 105 * math.sin(distance * 0.004)
        + 45 * math.sin(distance * 0.009)
    )


def draw_road(screen, road_progress):
    """Draw the road, its edges, and the dashed centre line."""
    left_edge = []
    right_edge = []

    for y in range(-10, HEIGHT + 20, 10):
        center = road_center(y, road_progress)
        left_edge.append((int(center - ROAD_WIDTH / 2), y))
        right_edge.append((int(center + ROAD_WIDTH / 2), y))

    pygame.draw.polygon(screen, EDGE_COLOR, left_edge + right_edge[::-1])

    inner_left = [
        (int(road_center(y, road_progress) - ROAD_WIDTH / 2 + 6), y)
        for y in range(-10, HEIGHT + 20, 10)
    ]

    inner_right = [
        (int(road_center(y, road_progress) + ROAD_WIDTH / 2 - 6), y)
        for y in range(-10, HEIGHT + 20, 10)
    ]

    pygame.draw.polygon(screen, ROAD_COLOR, inner_left + inner_right[::-1])

    draw_centre_line(screen, road_progress)


def draw_centre_line(screen, road_progress):
    """Draw the dashed centre line of the road."""
    for y in range(0, HEIGHT, 40):
        center = road_center(y, road_progress)
        pygame.draw.line(
            screen,
            LINE_COLOR,
            (int(center), y),
            (int(center), y + 20),
            3,
        )


def draw_car(screen, car_x, car_y):
    """Draw the car as a rectangle with a windscreen."""
    car_rect = pygame.Rect(
        int(car_x - CAR_WIDTH / 2),
        int(car_y - CAR_HEIGHT / 2),
        CAR_WIDTH,
        CAR_HEIGHT,
    )
    pygame.draw.rect(screen, CAR_COLOR, car_rect, border_radius=8)
    draw_windscreen(screen, car_rect)


def draw_windscreen(screen, car_rect):
    """Draw the windscreen of the car as a smaller rectangle on top of the car."""
    pygame.draw.rect(
        screen,
        (170, 220, 240),
        (
            car_rect.x + 6,
            car_rect.y + 8,
            CAR_WIDTH - 12,
            13,
        ),
        border_radius=3,
    )


def handle_steering(keys, car_x, car_velocity, dt):
    """Handle car steering and apply friction when no keys are pressed."""
    steering_acceleration = 500
    max_steering_speed = 230
    friction = 4.0

    if keys[pygame.K_LEFT]:
        car_velocity -= steering_acceleration * dt

    if keys[pygame.K_RIGHT]:
        car_velocity += steering_acceleration * dt

    car_velocity = max(
        -max_steering_speed, min(car_velocity, max_steering_speed)
    )

    if not keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
        car_velocity *= max(0, 1 - friction * dt)

    car_x += car_velocity * dt
    return car_x, car_velocity


def is_car_on_road(car_x, car_y, road_progress):
    """Check if the car is completely within the road boundaries."""
    center = road_center(car_y, road_progress)
    road_left = center - ROAD_WIDTH / 2
    road_right = center + ROAD_WIDTH / 2

    car_left = car_x - CAR_WIDTH / 2
    car_right = car_x + CAR_WIDTH / 2

    return car_left >= road_left and car_right <= road_right


def draw_hud(screen, font, small_font, elapsed_time, offroad_time):
    """Display elapsed time, remaining time, and off-road time."""
    remaining = max(0, SESSION_LENGTH - elapsed_time)

    panel = pygame.Rect(WIDTH - 235, 12, 220, 112)
    pygame.draw.rect(screen, (25, 25, 25), panel, border_radius=8)

    screen.blit(
        font.render(f"Remaining: {remaining:04.1f}s", True, (255, 255, 255)),
        (WIDTH - 225, 22),
    )

    screen.blit(
        small_font.render(
            f"Elapsed: {elapsed_time:05.1f}s", True, (255, 255, 255)
        ),
        (WIDTH - 225, 57),
    )

    screen.blit(
        small_font.render(
            f"Off-road: {offroad_time:05.2f}s", True, (255, 220, 120)
        ),
        (WIDTH - 225, 85),
    )


def draw_results(screen, font, small_font, elapsed_time, offroad_time):
    """Display the results after session ends."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    percentage = (
        (offroad_time / SESSION_LENGTH * 100) if SESSION_LENGTH > 0 else 0
    )

    results = [
        ("Session Complete", 220, (255, 255, 255), font),
        (f"Total time: {elapsed_time:.1f} seconds", 275, (255, 255, 255), font),
        (f"Off-road time: {offroad_time:.2f} seconds", 315, (255, 220, 120), font),
        (f"Off-road: {percentage:.1f}%", 355, (255, 255, 255), font),
        ("Close the window to exit.", 410, (220, 220, 220), small_font),
    ]

    for message, y, colour, selected_font in results:
        text = selected_font.render(message, True, colour)
        screen.blit(text, text.get_rect(center=(WIDTH // 2, y)))


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("IROP Dual-Task Car Game")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 23)
    small_font = pygame.font.SysFont("arial", 17)

    # Setup data logging directory and file
    os.makedirs("logs", exist_ok=True)
    session_timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join("logs", f"session_{session_timestamp_str}.csv")

    car_x = WIDTH / 2
    car_y = HEIGHT - 125
    car_velocity = 0.0

    road_progress = 0.0
    elapsed_time = 0.0
    offroad_time = 0.0

    running = True
    game_over = False

    with open(log_filename, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        # Write header matching session metrics and wall-clock time for milestone 15a sync
        writer.writerow(
            [
                "wall_clock_time",
                "session_elapsed_time",
                "car_x",
                "car_velocity",
                "road_center",
                "is_offroad",
                "event_type",
            ]
        )

        # Log session start event
        writer.writerow(
            [
                time.time(),
                elapsed_time,
                car_x,
                car_velocity,
                road_center(car_y, road_progress),
                False,
                "SESSION_START",
            ]
        )

        # Main game loop
        while running:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            if not game_over:
                elapsed_time += dt
                road_progress += ROAD_SPEED * dt

                keys = pygame.key.get_pressed()
                car_x, car_velocity = handle_steering(
                    keys, car_x, car_velocity, dt
                )

                on_road = is_car_on_road(car_x, car_y, road_progress)
                if not on_road:
                    offroad_time += dt

                # Log sample data per frame
                writer.writerow(
                    [
                        time.time(),
                        round(elapsed_time, 4),
                        round(car_x, 2),
                        round(car_velocity, 2),
                        round(road_center(car_y, road_progress), 2),
                        not on_road,
                        "SAMPLE",
                    ]
                )

                if elapsed_time >= SESSION_LENGTH:
                    elapsed_time = SESSION_LENGTH
                    game_over = True
                    writer.writerow(
                        [
                            time.time(),
                            elapsed_time,
                            car_x,
                            car_velocity,
                            road_center(car_y, road_progress),
                            not on_road,
                            "SESSION_END",
                        ]
                    )

            # Draw current frame
            screen.fill(GRASS)
            draw_road(screen, road_progress)
            draw_car(screen, car_x, car_y)

            if game_over:
                draw_results(
                    screen, font, small_font, elapsed_time, offroad_time
                )
            else:
                draw_hud(
                    screen, font, small_font, elapsed_time, offroad_time
                )

            pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
