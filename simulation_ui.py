import pygame
import sys
import math
import time
from map_config import nodes, edges

SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 800
ROAD_WIDTH_MAIN = 80
ROAD_WIDTH_SECONDARY = 40

# REFINED DARK-MODE PALETTE
COLOR_BACKGROUND = (14, 16, 22)
COLOR_ROAD = (28, 32, 42)
COLOR_ROAD_BORDER = (44, 50, 66)
COLOR_LINE = (205, 215, 230)
COLOR_LINE_EDGE = (56, 64, 82)
COLOR_WALL = (22, 26, 36)
COLOR_WALL_OUTLINE = (42, 48, 64)
COLOR_TEXT_UI = (225, 230, 242)
COLOR_TEXT_CAR = (130, 190, 255)
COLOR_RED = (255, 75, 85)
COLOR_GREEN = (65, 230, 130)
COLOR_YELLOW = (255, 215, 75)
COLOR_GRASS = (18, 26, 22)
COLOR_NORMAL_CAR = (45, 125, 235)
COLOR_AMBULANCE_CAR = (255, 60, 70)
COLOR_AGGRESSIVE_CAR = (235, 105, 30)

def get_font(size, bold=False):
    """Load a system font."""
    fonts = ["sfprodisplay", "arial", "helvetica"]
    return pygame.font.SysFont(fonts, size, bold=bold)

def draw_modern_button(
    surface, rect, text, font, base_color, text_color=(255, 255, 255), is_hovered=False
):
    """
    Draw a clean, modern rounded button with matching border and subtle shadow.
    """
    x, y, w, h = rect
    pad = 4
    btn_surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    alpha = 230 if not is_hovered else 255
    r, g, b = base_color
    # Subtle soft drop shadow behind button
    pygame.draw.rect(btn_surf, (0, 0, 0, 70), (pad, pad + 2, w, h), border_radius=10)
    # Main rounded body
    pygame.draw.rect(btn_surf, (r, g, b, alpha), (pad, pad, w, h), border_radius=10)
    # Crisp border outline that follows the rounded corner profile
    border_color = (
        min(255, r + 45),
        min(255, g + 45),
        min(255, b + 45),
        220 if is_hovered else 150,
    )
    pygame.draw.rect(btn_surf, border_color, (pad, pad, w, h), width=2, border_radius=10)
    is_antialiased = True
    text_surf = font.render(text, is_antialiased, text_color)
    text_rect = text_surf.get_rect(center=(pad + w // 2, pad + h // 2))
    btn_surf.blit(text_surf, text_rect)
    surface.blit(btn_surf, (x - pad, y - pad))

class SimulationUI:
    def __init__(self, title="RoadLogic - C-V2X Command Center"):
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        info = pygame.display.Info()
        screen_w = info.current_w
        screen_h = info.current_h
        self.window_w, self.window_h = SCREEN_WIDTH, SCREEN_HEIGHT
        if screen_w < SCREEN_WIDTH or screen_h < SCREEN_HEIGHT:
            scale_factor = min((screen_w - 50) / SCREEN_WIDTH, (screen_h - 100) / SCREEN_HEIGHT)
            self.window_w = int(SCREEN_WIDTH * scale_factor)
            self.window_h = int(SCREEN_HEIGHT * scale_factor)
        self.window = pygame.display.set_mode(
            (self.window_w, self.window_h), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE
        )
        self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen.fill(COLOR_BACKGROUND)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.title_font = get_font(22, bold=True)
        self.font = get_font(18, bold=True)
        self.small_font = get_font(15)
        self.micro_font = get_font(13)
        self.fps = 60
        self.system_on = True
        self.button_rect = pygame.Rect(20, 20, 160, 45)
        # Vehicle visual enhancement tracking (smooth rotation & soft trails)
        self.vehicle_angles = {}
        self.vehicle_trails = {}
        self.DEER_DECOR_POINTS = [
            (1270, 590, "FX"),
            (1330, 565, "N"),
            (1320, 590, "N"),
            (1290, 560, "FX"),
            (1410, 730, "FX"),
            (1390, 760, "N"),
        ]
        self.COLOR_RED_OFF = (60, 0, 0)
        self.COLOR_YELLOW_OFF = (60, 60, 0)
        self.COLOR_GREEN_OFF = (0, 60, 0)
        self.img_normal = None
        self.img_aggressive = None
        self.img_ambulance = None
        self.img_indicator = None
        self.img_deer = None
        self.use_images = False
        try:
            self.img_normal = pygame.image.load("images/car.png").convert_alpha()
            self.img_ambulance = pygame.image.load(
                "images/ambulance.png"
            ).convert_alpha()
            try:
                self.img_aggressive = pygame.image.load(
                    "images/car-aggressive.png"
                ).convert_alpha()
            except:
                print("car-aggressive.png missing, using normal image.")
                self.img_aggressive = self.img_normal
            indicator_base = pygame.image.load("images/indicator.png").convert_alpha()
            self.img_indicator = pygame.transform.scale(indicator_base, (30, 30))
            self.img_deer = pygame.image.load("images/deer.png").convert_alpha()
            self.use_images = True
        except Exception as e:
            print(f"Problems loading main images. Error: {e}")
        self.rotation_map = {"EAST": 0, "NORTH": 90, "WEST": 180, "SOUTH": 270}

    def draw_indicator(self):
        if self.img_indicator is None:
            return
        x1, y1 = 1400, 580
        x2, y2 = 1300, 700
        img_left = pygame.transform.rotate(self.img_indicator, 90)
        img_right = pygame.transform.rotate(self.img_indicator, -90)
        self.screen.blit(img_left, (x1, y1))
        self.screen.blit(img_right, (x2, y2))
        pygame.draw.rect(self.screen, (0, 0, 0), (1425, 593, 50, 4))
        pygame.draw.rect(self.screen, (0, 0, 0), (1255, 712, 50, 4))

    def is_outside_bounds(self, v_data):
        if not v_data:
            return True
        if v_data.get("vehicle_type") == "Infrastructure":
            return False
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        return x < -50 or x > SCREEN_WIDTH + 50 or y < -50 or y > SCREEN_HEIGHT + 50

    def draw_risk_aura(self, center, radius, color_rgb, max_alpha=120, rings=6):
        x, y = int(center[0]), int(center[1])
        aura = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        cx, cy = radius, radius
        for i in range(rings):
            t = i / max(1, rings - 1)
            r = int(radius * (1.0 - 0.12 * i))
            a = int(max_alpha * (1.0 - t) ** 2)
            pygame.draw.circle(aura, (*color_rgb, a), (cx, cy), r)
        self.screen.blit(aura, (x - radius, y - radius))

    def _intersection_centers_and_degree(self):
        intersections = ["I1", "I2", "I3"]
        results = []
        for inter in intersections:
            corners = [f"{inter}_NW", f"{inter}_NE", f"{inter}_SE", f"{inter}_SW"]
            pts = [nodes.get(c) for c in corners if nodes.get(c)]
            if len(pts) != 4:
                continue
            cx = sum(p[0] for p in pts) / 4
            cy = sum(p[1] for p in pts) / 4
            degree = 0
            for u, v, _ in edges:
                u_is = u.startswith(inter + "_")
                v_is = v.startswith(inter + "_")
                if u_is and not v_is:
                    degree += 1
                if v_is and not u_is:
                    degree += 1
            results.append(((cx, cy), degree))
        return results

    def draw_risk_overlays(self, current_traffic=None):
        for center, degree in self._intersection_centers_and_degree():
            if degree >= 8:
                self.draw_risk_aura(
                    center, radius=85, color_rgb=(255, 0, 0), max_alpha=120
                )
            else:
                self.draw_risk_aura(
                    center, radius=70, color_rgb=(255, 0, 0), max_alpha=70
                )
        if current_traffic:
            for v in current_traffic.values():
                if v and v.get("vehicle_type") == "Animal":
                    x = v.get("position_x", 0)
                    y = v.get("position_y", 0)
                    self.draw_risk_aura(
                        (x, y), radius=40, color_rgb=(255, 140, 0), max_alpha=100
                    )

    def draw_dashed_line_segment(
        self, p1, p2, color, dash_length=15, gap_length=10, offset=0
    ):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        unit_dx = dx / length
        unit_dy = dy / length
        norm_dx = -unit_dy * offset
        norm_dy = unit_dx * offset
        current_x, current_y = p1[0] + norm_dx, p1[1] + norm_dy
        total_drawn = 0
        while total_drawn < length:
            draw_len = min(dash_length, length - total_drawn)
            end_x = current_x + unit_dx * draw_len
            end_y = current_y + unit_dy * draw_len
            pygame.draw.line(
                self.screen,
                color,
                (int(current_x), int(current_y)),
                (int(end_x), int(end_y)),
                1,
            )
            total_drawn += dash_length + gap_length
            current_x += unit_dx * (dash_length + gap_length)
            current_y += unit_dy * (dash_length + gap_length)

    def draw_building_along_road(self, p1, p2, width=60, offset=80, node_offset=50):
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 2 * node_offset:
            return
        ux = dx / length
        uy = dy / length
        x1 += ux * node_offset
        y1 += uy * node_offset
        x2 -= ux * node_offset
        y2 -= uy * node_offset
        px = -uy
        py = ux
        ox = px * offset
        oy = py * offset
        pA = (x1 + ox, y1 + oy)
        pB = (x2 + ox, y2 + oy)
        pC = (x2 + ox + px * width, y2 + oy + py * width)
        pD = (x1 + ox + px * width, y1 + oy + py * width)
        pygame.draw.polygon(self.screen, COLOR_WALL, [pA, pB, pC, pD])
        pygame.draw.polygon(self.screen, COLOR_WALL_OUTLINE, [pA, pB, pC, pD], 1)

    def draw_environment(self):
        """Draw map with clean dark-mode road palette and crisp lane markings."""
        self.screen.fill(COLOR_BACKGROUND)
        pygame.draw.polygon(
            self.screen,
            COLOR_GRASS,
            [
                (1000, 0),
                (SCREEN_WIDTH, 0),
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                (600, SCREEN_HEIGHT),
            ],
            width=0,
        )
        pygame.draw.polygon(
            self.screen,
            COLOR_BACKGROUND,
            [(0, 100), (0, SCREEN_HEIGHT), (1140, 800), (1140, 675)],
            width=0,
        )
        # 1. Road Border / Shoulder Curb Layer
        for u, v, _ in edges:
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if p1 and p2:
                pygame.draw.line(self.screen, COLOR_ROAD_BORDER, p1, p2, ROAD_WIDTH_SECONDARY + 4)
        # 2. Road Asphalt Surface Layer
        for u, v, _ in edges:
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if p1 and p2:
                pygame.draw.line(self.screen, COLOR_ROAD, p1, p2, ROAD_WIDTH_SECONDARY)
        # 3. Architectural building blocks along roads
        self.draw_building_along_road(
            nodes["W_START"], nodes["I1_SW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["MERGE_UP"], nodes["I3_NE"], width=50, offset=40, node_offset=50
        )
        self.draw_building_along_road(
            nodes["MERGE_UP"],
            nodes["NE_ONEWAY_START"],
            width=50,
            offset=40,
            node_offset=110,
        )
        self.draw_building_along_road(
            nodes["NW_START"], nodes["I3_NW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["I3_SW"], nodes["I1_NW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["W_END"], nodes["I1_NW"], width=50, offset=-90, node_offset=60
        )
        self.draw_building_along_road(
            nodes["I1_SE"], nodes["I2_SW"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["I1_NE"], nodes["I3_SE"], width=50, offset=40, node_offset=100
        )
        self.draw_building_along_road(
            nodes["I3_SE"], nodes["I2_NW"], width=40, offset=40, node_offset=250
        )
        # 4. Center Dashed Lane Divider Markings
        drawn_dashed = set()
        for u, v, _ in edges:
            if (u, v) in drawn_dashed:
                continue
            if u.startswith("I") and v.startswith("I") and u[:2] == v[:2]:
                continue
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if not p1 or not p2:
                continue
            for u2, v2, _ in edges:
                if (u2, v2) in drawn_dashed or (u2, v2) == (u, v):
                    continue
                p1_rev = nodes.get(u2)
                p2_rev = nodes.get(v2)
                if not p1_rev or not p2_rev:
                    continue
                dist_starts = math.hypot(p1_rev[0] - p2[0], p1_rev[1] - p2[1])
                dist_ends = math.hypot(p2_rev[0] - p1[0], p2_rev[1] - p1[1])
                if dist_starts < 100 and dist_ends < 100:
                    center_start = ((p1[0] + p2_rev[0]) / 2, (p1[1] + p2_rev[1]) / 2)
                    center_end = ((p2[0] + p1_rev[0]) / 2, (p2[1] + p1_rev[1]) / 2)
                    self.draw_dashed_line_segment(
                        center_start, center_end, COLOR_LINE, dash_length=16, gap_length=12, offset=0
                    )
                    drawn_dashed.add((u, v))
                    drawn_dashed.add((u2, v2))
                    break
        if self.use_images and self.img_deer is not None:
            base = pygame.transform.scale(self.img_deer, (35, 35))
            deer_n = base
            deer_fx = pygame.transform.flip(base, True, False)
            for x, y, v in self.DEER_DECOR_POINTS:
                img = deer_n if v == "N" else deer_fx
                rect = img.get_rect(center=(int(x), int(y)))
                self.screen.blit(img, rect)
        else:
            for x, y in getattr(self, "DEER_DECOR_POINTS", []):
                pygame.draw.circle(self.screen, (139, 69, 19), (int(x), int(y)), 8)

    def draw_traffic_light_agent(self, current_traffic):
        """Traffic lights at Intersection 1 (Bottom-Left)."""
        sem_data = next(
            (
                v
                for v in current_traffic.values()
                if v.get("agent_id") == "Center_TrafficLight"
            ),
            {},
        )
        state_ns = sem_data.get("state_NS", "RED")
        state_ew = sem_data.get("state_EW", "RED")
        def draw_pole(pos, state, orientation, dx=0, dy=0, flip=False):
            if not pos:
                return
            x, y = pos
            x += dx
            y += dy
            box_w, box_h = (22, 60) if orientation == "V" else (60, 22)
            pygame.draw.rect(
                self.screen,
                (30, 30, 30),
                (x - box_w // 2, y - box_h // 2, box_w, box_h),
            )
            r_c, y_c, g_c = (
                self.COLOR_RED_OFF,
                self.COLOR_YELLOW_OFF,
                self.COLOR_GREEN_OFF,
            )
            if not self.system_on:
                if (pygame.time.get_ticks() // 500) % 2 == 0:
                    y_c = COLOR_YELLOW
            else:
                if state == "GREEN":
                    g_c = COLOR_GREEN
                elif state == "RED":
                    r_c = COLOR_RED
                elif state == "YELLOW" or state == "YELLOW_BLINKING":
                    y_c = COLOR_YELLOW
            offsets = [-18, 0, 18]
            cols = [r_c, y_c, g_c] if not flip else [g_c, y_c, r_c]
            for i in range(3):
                p = (x, y + offsets[i]) if orientation == "V" else (x + offsets[i], y)
                pygame.draw.circle(self.screen, cols[i], p, 7)
        OFFSET_X = 40
        OFFSET_Y = 60
        draw_pole(
            nodes.get("I1_NW"), state_ns, "V", dx=-OFFSET_X, dy=-OFFSET_Y, flip=True
        )
        draw_pole(nodes.get("I1_SE"), state_ns, "V", dx=+OFFSET_X, dy=+OFFSET_Y)
        draw_pole(
            nodes.get("I1_SW"), state_ew, "H", dx=-OFFSET_Y, dy=+OFFSET_X, flip=True
        )
        draw_pole(nodes.get("I1_NE"), state_ew, "H", dx=+OFFSET_Y, dy=-OFFSET_X)

    def draw_buttons(self, mouse_pos):
        """Draw all buttons using helper function."""
        c1 = COLOR_GREEN if self.system_on else COLOR_RED
        text1 = "SYSTEM: ON" if self.system_on else "SYSTEM: OFF"
        h1 = self.button_rect.collidepoint(mouse_pos)
        draw_modern_button(
            self.screen, self.button_rect, text1, self.font, c1, is_hovered=h1
        )

    def draw_vehicle_shape(self, x, y, smooth_angle, v_data):
        """Renders an anti-aliased rounded vehicle shape with subtle drop shadow."""
        v_type = v_data.get("vehicle_type", "Normal")
        driving_style = v_data.get("driving_style", "Cautious")
        intent = v_data.get("intent", "CRUISE")
        speed = v_data.get("speed", 0.0)
        is_crashed = v_data.get("is_crashed", False)
        priority = v_data.get("priority_active", False)
        L, W = 46, 22
        pad = 12
        sw, sh = L + pad * 2, W + pad * 2
        # 1. Subtle Drop Shadow (dual-layer soft alpha)
        shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx, cy = sw // 2, sh // 2
        # Outer soft blur layer
        pygame.draw.rect(
            shadow_surf, (0, 0, 0, 35), (cx - L // 2 - 2, cy - W // 2 - 2, L + 4, W + 4), border_radius=9
        )
        # Core drop shadow
        pygame.draw.rect(
            shadow_surf, (0, 0, 0, 80), (cx - L // 2, cy - W // 2, L, W), border_radius=7
        )
        rot_shadow = pygame.transform.rotozoom(shadow_surf, -smooth_angle, 1.0)
        shadow_rect = rot_shadow.get_rect(center=(int(x + 2), int(y + 3)))
        self.screen.blit(rot_shadow, shadow_rect)
        # 2. Anti-Aliased Rounded Vehicle Body
        car_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        rx, ry = cx - L // 2, cy - W // 2
        if is_crashed:
            body_color = (70, 65, 72)
            border_color = (255, 75, 50, 220)
            roof_color = (45, 42, 48)
        elif v_type == "Ambulance":
            body_color = (244, 248, 252)
            border_color = (255, 65, 75, 230)
            roof_color = (235, 45, 55)
        elif driving_style == "Aggressive":
            body_color = (235, 105, 30)
            border_color = (255, 160, 60, 230)
            roof_color = (35, 38, 45)
        else:
            body_color = (42, 122, 230)
            border_color = (95, 180, 255, 230)
            roof_color = (24, 32, 48)
        # Rounded body capsule
        pygame.draw.rect(car_surf, body_color, (rx, ry, L, W), border_radius=7)
        pygame.draw.rect(car_surf, border_color, (rx, ry, L, W), width=1, border_radius=7)
        # Tinted glass windows
        glass_color = (16, 22, 34, 240)
        # Front windshield (facing +X)
        fw_x = rx + int(L * 0.52)
        fw_w = int(L * 0.20)
        glass_y = ry + 3
        glass_h = W - 6
        pygame.draw.rect(car_surf, glass_color, (fw_x, glass_y, fw_w, glass_h), border_radius=3)
        # Rear window (facing -X)
        rw_x = rx + int(L * 0.14)
        rw_w = int(L * 0.16)
        pygame.draw.rect(car_surf, glass_color, (rw_x, glass_y, rw_w, glass_h), border_radius=3)
        # Roof segment
        rf_x = rw_x + rw_w
        rf_w = fw_x - rf_x
        pygame.draw.rect(car_surf, roof_color, (rf_x, glass_y, rf_w, glass_h), border_radius=2)
        # Windshield specular reflection line
        pygame.draw.line(
            car_surf, (255, 255, 255, 75), (fw_x + 2, glass_y + 2), (fw_x + fw_w - 3, glass_y + glass_h - 3), 1
        )
        # Ambulance roof strobe & insignia
        if v_type == "Ambulance":
            # Red cross insignia
            pygame.draw.rect(car_surf, (255, 255, 255), (rf_x + rf_w // 2 - 5, cy - 2, 10, 4))
            pygame.draw.rect(car_surf, (255, 255, 255), (rf_x + rf_w // 2 - 2, cy - 5, 4, 10))
            pygame.draw.rect(car_surf, (230, 40, 45), (rf_x + rf_w // 2 - 4, cy - 1, 8, 2))
            pygame.draw.rect(car_surf, (230, 40, 45), (rf_x + rf_w // 2 - 1, cy - 4, 2, 8))
            # Flashing LED emergency strobe bar
            is_blue = (pygame.time.get_ticks() // 140) % 2 == 0
            c_l = (40, 140, 255) if is_blue else (255, 40, 45)
            c_r = (255, 40, 45) if is_blue else (40, 140, 255)
            pygame.draw.circle(car_surf, c_l, (rf_x + 3, cy - 4), 2)
            pygame.draw.circle(car_surf, c_r, (rf_x + 3, cy + 4), 2)
        # LED Headlights (front edge, +X)
        hl_color = (255, 250, 210, 240)
        pygame.draw.circle(car_surf, hl_color, (rx + L - 2, ry + 4), 2)
        pygame.draw.circle(car_surf, hl_color, (rx + L - 2, ry + W - 5), 2)
        # LED Taillights (rear edge, -X)
        is_braking = intent == "BRAKING" or speed < 2.0
        tl_color = (255, 30, 30, 255) if is_braking else (220, 50, 50, 220)
        tl_r = 3 if is_braking else 2
        pygame.draw.circle(car_surf, tl_color, (rx + 2, ry + 4), tl_r)
        pygame.draw.circle(car_surf, tl_color, (rx + 2, ry + W - 5), tl_r)
        # Smooth anti-aliased rotation
        rot_car = pygame.transform.rotozoom(car_surf, -smooth_angle, 1.0)
        car_rect = rot_car.get_rect(center=(int(x), int(y)))
        self.screen.blit(rot_car, car_rect)
        # Collision explosion/indicator
        if is_crashed:
            pygame.draw.circle(self.screen, (255, 80, 20, 180), (int(x), int(y)), 26, 2)
            pygame.draw.circle(self.screen, (255, 120, 30, 220), (int(x), int(y)), 16, 2)
        # Priority halo
        if priority and (pygame.time.get_ticks() // 200) % 2 == 0:
            pygame.draw.circle(self.screen, (255, 80, 80, 150), (int(x), int(y)), 34, 2)

    def update_and_draw_trails(self, current_traffic, now):
        """Updates soft motion trails behind moving vehicles and renders them."""
        active_ids = set()
        for v in current_traffic.values():
            if not v or v.get("vehicle_type") in ("Infrastructure", "Animal"):
                continue
            v_id = v.get("agent_id")
            if not v_id:
                continue
            active_ids.add(v_id)
            sp = v.get("speed", 0.0)
            x, y = v.get("position_x", 0.0), v.get("position_y", 0.0)
            smooth_angle = self.vehicle_angles.get(v_id, 0.0)
            # Record point near rear bumper
            rad = math.radians(smooth_angle)
            rear_x = x - math.cos(rad) * 20.0
            rear_y = y - math.sin(rad) * 20.0
            pts = self.vehicle_trails.setdefault(v_id, [])
            if sp > 1.5:
                pts.append((rear_x, rear_y, sp, now, v.get("vehicle_type", "Normal")))
        # Remove stale trails
        for vid in list(self.vehicle_trails.keys()):
            if vid not in active_ids:
                del self.vehicle_trails[vid]
            else:
                self.vehicle_trails[vid] = [
                    p for p in self.vehicle_trails[vid] if now - p[3] < 0.55
                ][-14:]
        # Render trails on alpha surface
        trail_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for vid, pts in self.vehicle_trails.items():
            n = len(pts)
            if n < 2:
                continue
            for i in range(n - 1):
                p1, p2 = pts[i], pts[i + 1]
                t = (i + 1) / n
                alpha = int(t * t * 90)
                r = max(1.5, t * 4.5)
                v_type = p2[4]
                col = (255, 75, 90) if v_type == "Ambulance" else (65, 175, 255)
                col_alpha = (*col, alpha)
                pygame.draw.line(
                    trail_surf,
                    col_alpha,
                    (int(p1[0]), int(p1[1])),
                    (int(p2[0]), int(p2[1])),
                    max(1, int(r * 1.8)),
                )
                pygame.draw.circle(
                    trail_surf,
                    col_alpha,
                    (int(p2[0]), int(p2[1])),
                    max(1, int(r)),
                )
        self.screen.blit(trail_surf, (0, 0))

    def render_vehicle(self, v_data, dt=0.05):
        v_id = v_data.get("agent_id", "?")
        if v_id == "Center_TrafficLight":
            return
        x, y = v_data.get("position_x", 0), v_data.get("position_y", 0)
        v_type = v_data.get("vehicle_type", "Normal")
        is_crashed = v_data.get("is_crashed", False)
        if v_type == "Animal":
            if self.use_images and self.img_deer is not None:
                deer_scaled = pygame.transform.scale(self.img_deer, (35, 35))
                rect = deer_scaled.get_rect(center=(int(x), int(y)))
                self.screen.blit(deer_scaled, rect)
            else:
                pygame.draw.circle(self.screen, (139, 69, 19), (int(x), int(y)), 10)
            animal_text = self.small_font.render(v_id, True, (255, 150, 150))
            self.screen.blit(animal_text, (int(x) - 25, int(y) - 30))
            return
        # 1. Smooth rotation tracking
        target_angle = v_data.get("visual_angle")
        if target_angle is None:
            target_angle = self.rotation_map.get(v_data.get("heading", "EAST"), 0.0)
        if v_id not in self.vehicle_angles:
            self.vehicle_angles[v_id] = target_angle
        else:
            prev_angle = self.vehicle_angles[v_id]
            diff = (target_angle - prev_angle + 180) % 360 - 180
            self.vehicle_angles[v_id] = prev_angle + diff * min(1.0, 14.0 * dt)
        smooth_angle = self.vehicle_angles[v_id]
        # 2. Draw vehicle shape (anti-aliased rounded shape with drop shadow)
        self.draw_vehicle_shape(x, y, smooth_angle, v_data)
        # 3. Telemetry text labels
        is_antialiased = True
        label_color = (255, 150, 160) if v_type == "Ambulance" else COLOR_TEXT_CAR
        id_s = self.font.render(v_id, is_antialiased, label_color)
        intent = v_data.get("intent", "IDLE")
        in_s = self.micro_font.render(f"[{intent}]", is_antialiased, label_color)
        speed = v_data.get("speed", 0.0)
        display_speed = 0.0 if is_crashed else speed
        sp_s = self.micro_font.render(
            f"V: {display_speed:.1f}", is_antialiased, label_color
        )
        self.screen.blit(id_s, (int(x) - 20, int(y) - 45))
        self.screen.blit(in_s, (int(x) - 20, int(y) - 60))
        self.screen.blit(sp_s, (int(x) - 20, int(y) + 25))

    def draw_dashboard(self, current_traffic):
        """Draw a panel in top-right corner."""
        if current_traffic is None:
            return
        total_cars, crashed_cars, total_speed, active_brakes, ambulances_active = (
            0,
            0,
            0.0,
            0,
            0,
        )
        for v in current_traffic.values():
            if not v:
                continue
            v_type = v.get("vehicle_type", "")
            if v_type in ["Normal", "Ambulance"]:
                total_cars += 1
                total_speed += v.get("speed", 0)
                if v.get("is_crashed", False):
                    crashed_cars += 1
                elif v.get("intent") == "BRAKING":
                    active_brakes += 1
            if v_type == "Ambulance":
                ambulances_active += 1
        avg_speed = (total_speed / total_cars) if total_cars > 0 else 0.0
        dash_width, dash_height = 280, 240
        hud = pygame.Surface((dash_width, dash_height), pygame.SRCALPHA)
        pygame.draw.rect(
            hud, (0, 0, 0, 200), (0, 0, dash_width, dash_height), border_radius=12
        )
        pygame.draw.rect(
            hud,
            (100, 150, 255, 255),
            (0, 0, dash_width, dash_height),
            width=2,
            border_radius=12,
        )
        title = self.title_font.render("● RoadLogic Command Center", True, (255, 215, 0))
        hud.blit(title, (40, 15))
        pygame.draw.line(hud, (100, 150, 255), (15, 42), (dash_width - 15, 42), 2)
        is_aa = True
        y_offset, spacing = 55, 23
        text_w = (255, 255, 255)
        hud.blit(
            self.small_font.render(
                f"● Connected vehicles: {total_cars}", is_aa, text_w
            ),
            (15, y_offset),
        )
        y_offset += spacing
        speed_color = (
            (100, 255, 100)
            if avg_speed > 30
            else ((255, 255, 100) if avg_speed > 10 else (255, 100, 100))
        )
        hud.blit(
            self.small_font.render(
                f"● Avg speed: {avg_speed:.1f} km/h", is_aa, speed_color
            ),
            (15, y_offset),
        )
        y_offset += spacing
        hud.blit(
            self.small_font.render(
                f"● Active AI interventions: {active_brakes}", is_aa, (100, 200, 255)
            ),
            (15, y_offset),
        )
        y_offset += spacing
        crash_color = (255, 80, 80) if crashed_cars > 0 else (100, 255, 100)
        hud.blit(
            self.small_font.render(
                f"● Accidents detected: {crashed_cars}", is_aa, crash_color
            ),
            (15, y_offset),
        )
        y_offset += spacing
        if ambulances_active > 0:
            if (pygame.time.get_ticks() // 300) % 2 == 0:
                hud.blit(
                    self.small_font.render(
                        f"● EMERGENCY: Green corridor!", is_aa, (255, 50, 50)
                    ),
                    (15, y_offset),
                )
        else:
            hud.blit(
                self.small_font.render(f"● Normal traffic", is_aa, (150, 150, 150)),
                (15, y_offset),
            )
        y_offset += spacing
        pygame.draw.line(
            hud, (100, 100, 100), (15, y_offset), (dash_width - 15, y_offset), 1
        )
        y_offset += 10
        lat = 12 + (pygame.time.get_ticks() % 5)
        msg = total_cars * 20
        hud.blit(
            self.micro_font.render("● Network: ONLINE (5G Secured)", is_aa, (100, 255, 100)), (15, y_offset)
        )
        y_offset += 20
        hud.blit(
            self.micro_font.render(
                f"   Ping: {lat}ms | Pkts: {msg}/s", is_aa, (200, 200, 200)
            ),
            (15, y_offset),
        )
        self.screen.blit(hud, (SCREEN_WIDTH - dash_width - 20, 20))

    def draw_graph_debug_overlay(self):
        """Overlay the raw navigation graph: directed arrowed edges + labeled node dots."""
        # Composite onto an alpha surface so it doesn't disturb road colours
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        EDGE_COLOR   = (0, 220, 255, 160)   # cyan, semi-transparent
        ARROW_COLOR  = (0, 255, 200, 220)   # bright teal arrowhead
        NODE_FILL    = (255, 60, 200, 210)   # magenta fill
        NODE_BORDER  = (255, 255, 255, 230)  # white ring
        LABEL_TEXT   = (255, 255, 255, 255)
        LABEL_BG     = (10, 12, 20, 200)     # dark frosted pill
        NODE_R    = 5   # node dot radius
        ARROW_LEN = 10  # arrowhead arm length (px)
        ARROW_ANG = math.radians(28)  # half-angle of arrowhead
        # 1. Directed edges
        for u, v, _ in edges:
            p1 = nodes.get(u)
            p2 = nodes.get(v)
            if not p1 or not p2:
                continue
            x1, y1 = float(p1[0]), float(p1[1])
            x2, y2 = float(p2[0]), float(p2[1])
            # Shorten both ends by NODE_R so the line doesn't overdraw the dots
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 1:
                continue
            ux, uy = dx / length, dy / length
            sx, sy = x1 + ux * NODE_R, y1 + uy * NODE_R
            ex, ey = x2 - ux * NODE_R, y2 - uy * NODE_R
            pygame.draw.line(overlay, EDGE_COLOR,
                             (int(sx), int(sy)), (int(ex), int(ey)), 1)
            # Arrowhead placed at 2/3 along the shortened segment
            ax = sx + (ex - sx) * 0.67
            ay = sy + (ey - sy) * 0.67
            angle = math.atan2(uy, ux)  # direction of travel
            for sign in (+1, -1):
                wing_angle = angle + math.pi - sign * ARROW_ANG
                wx = ax + math.cos(wing_angle) * ARROW_LEN
                wy = ay + math.sin(wing_angle) * ARROW_LEN
                pygame.draw.line(overlay, ARROW_COLOR,
                                 (int(ax), int(ay)), (int(wx), int(wy)), 2)
        # 2. Node dots
        for node_name, pos in nodes.items():
            px, py = pos
            # Filled dot with white ring
            pygame.draw.circle(overlay, NODE_BORDER, (px, py), NODE_R + 2)
            pygame.draw.circle(overlay, NODE_FILL,   (px, py), NODE_R)
            # Label on a dark frosted pill
            label_surf = self.micro_font.render(node_name, True, LABEL_TEXT[:3])
            lw, lh = label_surf.get_size()
            pad_x, pad_y = 4, 2
            pill_w, pill_h = lw + pad_x * 2, lh + pad_y * 2
            # Position: prefer right of node, clamp to screen
            lx = px + NODE_R + 4
            ly = py - pill_h // 2
            if lx + pill_w > SCREEN_WIDTH - 4:
                lx = px - NODE_R - 4 - pill_w
            if ly < 2:
                ly = 2
            if ly + pill_h > SCREEN_HEIGHT - 2:
                ly = SCREEN_HEIGHT - pill_h - 2
            # Dark background pill
            pill_surf = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
            pygame.draw.rect(pill_surf, LABEL_BG, (0, 0, pill_w, pill_h), border_radius=4)
            overlay.blit(pill_surf, (lx, ly))
            overlay.blit(label_surf, (lx + pad_x, ly + pad_y))
        self.screen.blit(overlay, (0, 0))

    def start(self, broker):
        running = True
        print("UI Simulation started. Network map (grid).")
        last_time = time.time()
        while running:
            now = time.time()
            dt = min(0.1, max(0.001, now - last_time))
            last_time = now
            mx, my = pygame.mouse.get_pos()
            virtual_mouse_pos = (
                int(mx * (SCREEN_WIDTH / self.window_w)),
                int(my * (SCREEN_HEIGHT / self.window_h))
            )
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    self.window_w, self.window_h = event.w, event.h
                    self.window = pygame.display.set_mode((self.window_w, self.window_h), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    event_pos = (
                        int(event.pos[0] * (SCREEN_WIDTH / self.window_w)),
                        int(event.pos[1] * (SCREEN_HEIGHT / self.window_h))
                    )
                    if self.button_rect.collidepoint(event_pos):
                        self.system_on = not self.system_on
                        if hasattr(broker, "infrastructure_active"):
                            broker.infrastructure_active = self.system_on
            self.draw_environment()
            self.draw_graph_debug_overlay()
            self.draw_buttons(virtual_mouse_pos)
            self.draw_indicator()
            with broker.lock:
                to_remove = [
                    k
                    for k, v in broker.vehicles_status.items()
                    if self.is_outside_bounds(v)
                ]
                for k in to_remove:
                    del broker.vehicles_status[k]
                current_traffic = broker.vehicles_status.copy()
            self.update_and_draw_trails(current_traffic, now)
            self.draw_risk_overlays(current_traffic)
            self.draw_traffic_light_agent(current_traffic)
            for v_data in current_traffic.values():
                self.render_vehicle(v_data, dt)
            self.draw_dashboard(current_traffic)
            scaled_screen = pygame.transform.smoothscale(self.screen, (self.window_w, self.window_h))
            self.window.blit(scaled_screen, (0, 0))
            pygame.display.flip()
            self.clock.tick(self.fps)
        pygame.quit()
if __name__ == "__main__":
    class DummyBroker:
        def __init__(self):
            self.vehicles_status = {}
            self.lock = type(
                "obj",
                (object,),
                {"__enter__": lambda s: None, "__exit__": lambda s, x, y, z: None},
            )()
    SimulationUI().start(DummyBroker())
