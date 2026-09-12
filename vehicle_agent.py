import math
import time
import threading
import requests

from navigation_system import Navigator
from v2x_security import SecurityManager


class VehicleAgent:

    def __init__(
        self,
        agent_id,
        start_node,
        target_node,
        desired_speed,
        vehicle_type="Normal",
        driving_style="Cautious",
    ):
        self.agent_id = agent_id
        self.desired_speed = desired_speed
        self.speed = desired_speed
        self.vehicle_type = vehicle_type
        self.driving_style = driving_style
        self.current_state = "CRUISE"

        # Initialize Navigation instead of dozens of individual variables!
        self.navigator = Navigator(agent_id, start_node, target_node)

        self.memory = {}
        self.target_int = (0, 0)
        self.is_crashed = False

    @property
    def position_x(self):
        return self.navigator.position_x

    @position_x.setter
    def position_x(self, val):
        self.navigator.position_x = val
        self.navigator.base_x = val

    @property
    def position_y(self):
        return self.navigator.position_y

    @position_y.setter
    def position_y(self, val):
        self.navigator.position_y = val
        self.navigator.base_y = val

    @property
    def heading(self):
        return self.navigator.heading

    @property
    def visual_angle(self):
        return self.navigator.visual_angle

    @property
    def turn_intent(self):
        return self.navigator.turn_intent

    @turn_intent.setter
    def turn_intent(self, val):
        self.navigator.turn_intent = val

    @property
    def route(self):
        return self.navigator.route

    @property
    def current_node_index(self):
        return self.navigator.current_node_index

    @property
    def target_lane_offset(self):
        return self.navigator.target_lane_offset

    @target_lane_offset.setter
    def target_lane_offset(self, val):
        self.navigator.target_lane_offset = val

    @property
    def base_x(self):
        return self.navigator.base_x

    @base_x.setter
    def base_x(self, val):
        self.navigator.base_x = val

    @property
    def base_y(self):
        return self.navigator.base_y

    @base_y.setter
    def base_y(self, val):
        self.navigator.base_y = val

    # === UPDATE POSITION METHOD (becomes very clean) ===
    def update_position(self, dt):
        if self.speed <= 0:
            return

        # Navigation does the heavy lifting
        self.navigator.update_position(dt, self.speed)

        # CLOUD TELEMETRY: Remains unchanged
        if hasattr(self, "last_telemetry_time"):
            if time.time() - self.last_telemetry_time < 1.0:
                return
        self.last_telemetry_time = time.time()

        is_braking = 1 if self.current_state == "BRAKING" else 0
        data_string = f"vehicle_stats,agent_id={self.agent_id} speed={self.speed},braking={is_braking}"
        headers = {"Authorization": "Token super-secret-auth-token"}

        def send_to_cloud():
            try:
                requests.post(
                    "http://localhost:8086/api/v2/write?org=v2x_org&bucket=telemetry&precision=s",
                    headers=headers,
                    data=data_string,
                    timeout=0.5,
                )
            except:
                pass

        threading.Thread(target=send_to_cloud, daemon=True).start()

    def receive_v2x_message(self, message):
        sender_id = message.get("agent_id")
        if not sender_id or sender_id == self.agent_id:
            return

        if message.get("vehicle_type") == "Animal":
            self.memory[sender_id] = message
            return

        if SecurityManager.is_payload_valid(message, self.agent_id):
            self.memory[sender_id] = message

    def decide_action(self, int_x, int_y):
        self.target_int = (int_x, int_y)

        if self.is_crashed:
            self.speed = 0
            self.current_state = "CRASHED"
            return



        # Calculate distance to current intersection center early on
        dist_to_int = math.sqrt(
            (int_x - self.position_x) ** 2 + (int_y - self.position_y) ** 2
        )

        # 0. ABSOLUTE EMERGENCY: Animal Avoidance
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Animal":
                ax = other_data.get("position_x", 0)
                ay = other_data.get("position_y", 0)

                dist_to_animal = math.sqrt(
                    (ax - self.position_x) ** 2 + (ay - self.position_y) ** 2
                )

                if (
                    dist_to_animal < 100.0
                ):  # Reduced so cars behind use ACC
                    if self.heading == "EAST" and ax > self.position_x:
                        self._brake("ANIMAL ON ROAD!")
                        return
                    elif self.heading == "WEST" and ax < self.position_x:
                        self._brake("ANIMAL ON ROAD!")
                        return

        # 0.1 PULL OVER FOR AMBULANCE
        is_pulling_over = False
        # Forbid pulling over if car is already deep in intersection (dist_to_int < 35.0)
        # to prevent sliding over perpendicular lanes. Allowed at traffic lights.
        if self.vehicle_type != "Ambulance" and dist_to_int > 35.0:
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Ambulance" and not other_data.get(
                    "is_crashed", False
                ):
                    ox, oy = other_data.get("position_x", 0), other_data.get(
                        "position_y", 0
                    )
                    oh = other_data.get("heading", "")
                    opposite_headings = {
                        "NORTH": "SOUTH",
                        "SOUTH": "NORTH",
                        "EAST": "WEST",
                        "WEST": "EAST",
                    }

                    dot_amb = 0
                    dist_amb = 999.0
                    
                    other_angle = other_data.get("visual_angle", 0)
                    angle_diff = abs((self.visual_angle % 360) - (other_angle % 360))
                    if angle_diff > 180:
                        angle_diff = 360 - angle_diff
                        
                    # Ambulance must be on the same axis (parallel or anti-parallel)
                    if angle_diff > 25.0 and angle_diff < 155.0:
                        continue

                    if self.heading == oh:
                        dx_amb = self.position_x - ox
                        dy_amb = self.position_y - oy
                        rad = math.radians(self.visual_angle)
                        dot_amb = dx_amb * math.cos(rad) + dy_amb * math.sin(rad)
                        dist_amb = math.sqrt(dx_amb**2 + dy_amb**2)
                        cross_amb = abs(dx_amb * (-math.sin(rad)) + dy_amb * math.cos(rad))
                    elif opposite_headings.get(self.heading) == oh:
                        dx_amb = ox - self.position_x
                        dy_amb = oy - self.position_y
                        rad = math.radians(self.visual_angle)
                        dot_amb = dx_amb * math.cos(rad) + dy_amb * math.sin(rad)
                        dist_amb = math.sqrt(dx_amb**2 + dy_amb**2)
                        cross_amb = abs(dx_amb * (-math.sin(rad)) + dy_amb * math.cos(rad))
                    # Remains pulled over while ambulance is nearby (180px)
                    if dist_amb < 180.0:
                        self.target_lane_offset = -20.0
                        is_pulling_over = True
                        break

        # 0.5 ACC & OBSTACLE OVERTAKING (Waze Rerouting)
        obstacle_in_front = False
        for other_id, other_data in list(self.memory.items()):
            if other_data.get("vehicle_type") == "Infrastructure":
                continue

            ox, oy = other_data.get("position_x", 0), other_data.get("position_y", 0)
            other_angle = other_data.get("visual_angle", 0)

            # Calculate real rotation difference of cars
            angle_diff = abs((self.visual_angle % 360) - (other_angle % 360))
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            # If moving relatively on the same axis / direction
            if angle_diff <= 35.0:
                dx = ox - self.position_x
                dy = oy - self.position_y

                rad = math.radians(self.visual_angle)
                vx = math.cos(rad)
                vy = math.sin(rad)

                # Dot product (shows if in front) and cross product (if on lane)
                dot = dx * vx + dy * vy
                cross = abs(dx * (-vy) + dy * vx)

                # Widen lateral visual angle if car pulls over or is ambulance
                if is_pulling_over or self.vehicle_type == "Ambulance":
                    cross_threshold = 60.0
                else:
                    cross_threshold = 25.0

                if dot > 0 and cross < cross_threshold:
                    # Ambulance ignores cars already fully pulled over
                    if self.vehicle_type == "Ambulance" and other_data.get("target_lane_offset", 0.0) < -10.0:
                        continue

                    dist_to_front = math.sqrt(dx**2 + dy**2)

                    if other_data.get("is_crashed", False) and dist_to_front < 160.0:
                        obstacle_in_front = True
                        self.target_lane_offset = 25.0
                        continue

                    safe_distance = 150.0

                    if dist_to_front < safe_distance:
                        leader_speed = other_data.get("speed", 0.0)

                        # Ambulance fluidly overtakes slow or stopped cars in front!
                        if (
                            self.vehicle_type == "Ambulance"
                            and dist_to_front < 140.0
                        ):
                            # --- PREVENT FRONTAL COLLISION (SAFE OVERTAKING) ---
                            free_oncoming_lane = True
                            opposite_headings = {
                                "NORTH": "SOUTH",
                                "SOUTH": "NORTH",
                                "EAST": "WEST",
                                "WEST": "EAST",
                            }
                            my_opposite = opposite_headings.get(self.heading)

                            for opp_id, opp_data in list(self.memory.items()):
                                if opp_data.get(
                                    "heading"
                                ) == my_opposite and not opp_data.get(
                                    "is_crashed", False
                                ):
                                    dx_opp = (
                                        opp_data.get("position_x", 0) - self.position_x
                                    )
                                    dy_opp = (
                                        opp_data.get("position_y", 0) - self.position_y
                                    )

                                    rad_opp = math.radians(self.visual_angle)
                                    dot_opp = dx_opp * math.cos(
                                        rad_opp
                                    ) + dy_opp * math.sin(rad_opp)
                                    dist_opp = math.sqrt(dx_opp**2 + dy_opp**2)

                                    # Coming towards us at dangerous distance
                                    if dot_opp > 0 and dist_opp < 300.0:
                                        if (
                                            opp_data.get("vehicle_type") == "Ambulance"
                                            or dist_opp < 150.0
                                        ):
                                            free_oncoming_lane = False
                                            break

                            if free_oncoming_lane:
                                obstacle_in_front = True
                                self.target_lane_offset = 25.0

                        if not obstacle_in_front:
                            if dist_to_front < 35.0:
                                self.speed = 0.0
                                self.current_state = "BRAKING"
                                return

                            if is_pulling_over:
                                self.current_state = "BRAKING"
                                if dist_to_front < 48.0:
                                    self.speed = 0.0
                                else:
                                    # Approaches faster (with 20.0) to leave compact space behind
                                    self.speed = max(20.0, self.speed - 2.0)
                                return

                        if self.driving_style == "Aggressive":
                            if dist_to_front < 48.0:
                                self.speed = max(
                                    0.0, min(self.speed, leader_speed) - 5.0
                                )
                                self.current_state = "BRAKING"
                                return
                            elif (
                                dist_to_front < 75.0 and self.speed > leader_speed + 2.0
                            ):
                                self.speed = max(leader_speed, self.speed - 4.0)
                                self.current_state = "BRAKING"
                                return
                        else:
                            if dist_to_front < 55.0:
                                self.speed = max(
                                    0.0, min(self.speed, leader_speed) - 2.0
                                )
                                self.current_state = "BRAKING"
                                return
                            elif (
                                dist_to_front < 85.0 and self.speed > leader_speed + 2.0
                            ):
                                self.speed = max(leader_speed, self.speed - 2.0)
                                self.current_state = "BRAKING"
                                return

        if not obstacle_in_front and not is_pulling_over:
            # --- ENSURE SAFE LANE RE-ENTRY ---
            safe_to_return = True
            if self.target_lane_offset < -10.0:  # If we are still pulled over
                for other_id, other_data in list(self.memory.items()):
                    if other_data.get(
                        "vehicle_type"
                    ) == "Infrastructure" or other_data.get("is_crashed", False):
                        continue

                    if other_data.get("heading") == self.heading:
                        ox = other_data.get("position_x", 0)
                        oy = other_data.get("position_y", 0)

                        dx_rear = ox - self.position_x
                        dy_rear = oy - self.position_y
                        rad = math.radians(self.visual_angle)

                        # Negative dot product means it is BEHIND us
                        dot_rear = dx_rear * math.cos(rad) + dy_rear * math.sin(rad)
                        dist_rear = math.sqrt(dx_rear**2 + dy_rear**2)

                        # If a car comes from behind on our lane and is close (< 150px)
                        if dot_rear < 0 and dist_rear < 150.0:
                            # DEADLOCK AVOIDANCE: Can re-enter if rear car is not speeding bullet
                            rear_speed = other_data.get("speed", 0.0)
                            if rear_speed > self.speed + 15.0:
                                safe_to_return = False
                                break

            if safe_to_return:
                self.target_lane_offset = 0.0
            else:
                self.target_lane_offset = -20.0
                self.current_state = "BRAKING"

                # --- PREVENT INTERSECTION SLIDE ---
                # If pulled over and reached stop line, STOP completely!
                if 35.0 < dist_to_int < 80.0:
                    self.speed = 0.0
                else:
                    self.speed = max(
                        15.0, self.speed - 2.0
                    )  # Wait pulled over for traffic to pass
                return

        if is_pulling_over:
            self.current_state = "BRAKING"
            if 35.0 < dist_to_int < 80.0:
                self.speed = 0.0
            else:
                self.speed = max(20.0, self.speed - 2.0)
            return

        is_past = False
        if self.heading == "EAST" and self.position_x > int_x + 50:
            is_past = True
        if self.heading == "WEST" and self.position_x < int_x - 50:
            is_past = True
        if self.heading == "SOUTH" and self.position_y > int_y + 50:
            is_past = True
        if self.heading == "NORTH" and self.position_y < int_y - 50:
            is_past = True

        if is_past:
            self._recover_speed()
            self.last_ai_decision = None
            return

        in_intersection = dist_to_int <= 60.0

        # HIERARCHY 1: AMBULANCE PRIORITY
        if self.vehicle_type != "Ambulance":
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Ambulance":
                    if other_data.get("is_crashed", False):
                        continue

                    ox, oy = other_data.get("position_x", 0), other_data.get(
                        "position_y", 0
                    )
                    oh = other_data.get("heading", "")

                    amb_int = other_data.get("target_int", (0, 0))
                    if (
                        math.sqrt((int_x - amb_int[0]) ** 2 + (int_y - amb_int[1]) ** 2)
                        > 50.0
                    ):
                        continue
                    o_speed = other_data.get("speed", 0)
                    o_dist_to_int = math.sqrt((int_x - ox) ** 2 + (int_y - oy) ** 2)

                    amb_past = False
                    if oh == "SOUTH" and oy > int_y + 40:
                        amb_past = True
                    if oh == "NORTH" and oy < int_y - 40:
                        amb_past = True
                    if oh == "EAST" and ox > int_x + 40:
                        amb_past = True
                    if oh == "WEST" and ox < int_x - 40:
                        amb_past = True

                    my_ttc = dist_to_int / max(self.speed, 1.0)
                    amb_ttc = o_dist_to_int / max(o_speed, 1.0)

                    if not amb_past and o_dist_to_int < 400.0:
                        if my_ttc < amb_ttc - 2.0:
                            continue
                        if dist_to_int < 150.0:
                            self._brake("Yielding to Ambulance!")
                            return
                        else:
                            self.speed = max(1.0, self.speed - 0.2)
                            return

        if self.vehicle_type == "Ambulance":
            # --- AVOID COLLISION BETWEEN 2 AMBULANCES IN INTERSECTION ---
            if dist_to_int < 150.0:
                for other_id, other_data in list(self.memory.items()):
                    if other_data.get(
                        "vehicle_type"
                    ) == "Ambulance" and not other_data.get("is_crashed", False):
                        ox, oy = other_data.get("position_x", 0), other_data.get(
                            "position_y", 0
                        )

                        # Ensure other ambulance heading to same intersection
                        amb_int = other_data.get("target_int", (0, 0))
                        if (
                            math.sqrt(
                                (int_x - amb_int[0]) ** 2 + (int_y - amb_int[1]) ** 2
                            )
                            > 50.0
                        ):
                            continue

                        o_dist = math.sqrt((ox - int_x) ** 2 + (oy - int_y) ** 2)

                        if o_dist < 150.0:
                            if o_dist < dist_to_int - 20.0:
                                self._brake("Yielding to another ambulance!")
                                return
                            elif (
                                abs(dist_to_int - o_dist) <= 20.0
                                and self.agent_id > other_id
                            ):
                                self._brake("Ambulance tie-breaker")
                                return

            self.turn_intent = "PRIORITY"
            self._recover_speed()
            return

        # HIERARCHY 2: TRAFFIC LIGHT (V2I)
        semafor_data = self.memory.get("Center_TrafficLight")
        is_light_here = False
        has_green_light = False

        if semafor_data and abs(int_x - 400) < 20 and abs(int_y - 650) < 20:
            is_light_here = True

        if is_light_here:
            my_axis_color = "GREEN"
            if self.heading in ["NORTH", "SOUTH"]:
                my_axis_color = semafor_data.get("state_NS", "GREEN")
            elif self.heading in ["EAST", "WEST"]:
                my_axis_color = semafor_data.get("state_EW", "GREEN")
            time_to_change = semafor_data.get("time_to_change", 5.0)

            # Check if forced intersection or passed stop line
            has_passed_stop_line = False
            if self.heading == "EAST" and self.position_x > int_x - 45:
                has_passed_stop_line = True
            elif self.heading == "WEST" and self.position_x < int_x + 45:
                has_passed_stop_line = True
            elif self.heading == "SOUTH" and self.position_y > int_y - 45:
                has_passed_stop_line = True
            elif self.heading == "NORTH" and self.position_y < int_y + 45:
                has_passed_stop_line = True

            if has_passed_stop_line:
                has_green_light = True
            elif my_axis_color == "RED":
                if self.driving_style == "Aggressive":
                    if dist_to_int < 80.0:
                        if dist_to_int < 65.0:
                            self.speed = 0.0
                        else:
                            self._brake("V2I: Stopping at RED light (Aggressive)")
                        return
                else:
                    if dist_to_int < 120.0:
                        if dist_to_int < 65.0:
                            self.speed = 0.0
                        else:
                            self._brake("V2I: Stopping at RED light")
                        return
                    elif dist_to_int < 400.0:
                        frames_left = time_to_change * 20
                        if frames_left > 0:
                            optimal_speed = min(
                                self.desired_speed, max(1.0, dist_to_int / frames_left)
                            )
                            if self.speed > optimal_speed:
                                self.speed = max(optimal_speed, self.speed - 0.2)
                            elif self.speed < optimal_speed:
                                self.speed = min(optimal_speed, self.speed + 1.0)
                            return

            elif my_axis_color == "YELLOW":
                if self.driving_style == "Aggressive":
                    has_green_light = True
                else:
                    time_to_center = dist_to_int / max(self.speed, 1.0)
                    if time_to_center <= time_to_change + 0.5:
                        has_green_light = True
                    elif dist_to_int <= 150.0:
                        if dist_to_int < 65.0:
                            self.speed = 0.0
                        else:
                            self._brake("V2I: Stopping at YELLOW light")
                        return
            elif my_axis_color == "GREEN":
                has_green_light = True

        if has_green_light:
            self.turn_intent = "PRIORITY"
            self._recover_speed()
            return

        # HIERARCHY 2.5: RIGHT-OF-WAY REFLEX
        if self.vehicle_type != "Ambulance" and dist_to_int < 130.0:
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Infrastructure":
                    continue
                if other_data.get("is_crashed", False):
                    continue

                ox = other_data.get("position_x", 0)
                oy = other_data.get("position_y", 0)
                other_dist_to_int = math.sqrt((ox - int_x) ** 2 + (oy - int_y) ** 2)

                if other_dist_to_int < 130.0:
                    oh = other_data.get("heading", "")

                    coming_from_right = False
                    if self.heading == "NORTH" and oh == "WEST":
                        coming_from_right = True
                    elif self.heading == "SOUTH" and oh == "EAST":
                        coming_from_right = True
                    elif self.heading == "EAST" and oh == "NORTH":
                        coming_from_right = True
                    elif self.heading == "WEST" and oh == "SOUTH":
                        coming_from_right = True

                    if (
                        other_data.get("vehicle_type") == "Ambulance"
                        and self.vehicle_type != "Ambulance"
                    ):
                        coming_from_right = True

                    if coming_from_right:
                        # --- DONT YIELD IF WE ARE MUCH CLOSER TO CENTER ---
                        if dist_to_int < other_dist_to_int - 25.0:
                            continue

                        past_center = False
                        if oh == "WEST" and ox < int_x - 20:
                            past_center = True
                        elif oh == "EAST" and ox > int_x + 20:
                            past_center = True
                        elif oh == "NORTH" and oy < int_y - 20:
                            past_center = True
                        elif oh == "SOUTH" and oy > int_y + 20:
                            past_center = True

                        if not past_center:
                            # --- ANTI-DEADLOCK TIE-BREAKER ---
                            # If other is stationary and we are blocked, force passage by ID
                            if (
                                other_data.get("speed", 0) < 1.0
                                and self.agent_id > other_id
                            ):
                                continue

                            if dist_to_int > 45.0:
                                self.speed = max(0.0, self.speed - 3.5)
                            else:
                                self.speed = 0.0

                            self._brake(f"Right-of-way for {other_id}")
                            return

        # HIERARCHY 3A: ZIPPER MERGE
        if abs(int_x - 770) < 20 and abs(int_y - 455) < 20:
            # --- NEW: AVOID POST-DIAGONAL BLOCK ---
            if self.heading == "WEST" and self.position_x < int_x - 5:
                self._recover_speed()
                return
            if self.heading == "EAST" and self.position_x > int_x + 5:
                self._recover_speed()
                return
            if self.heading == "NORTH" and self.position_y < int_y - 5:
                self._recover_speed()
                return
            if self.heading == "SOUTH" and self.position_y > int_y + 5:
                self._recover_speed()
                return
            # ------------------------------------------

            conflict_merge = False
            for other_id, other_data in list(self.memory.items()):
                if other_data.get("vehicle_type") == "Infrastructure" or other_data.get(
                    "is_crashed", False
                ):
                    continue

                ox = other_data.get("position_x", 0)
                oy = other_data.get("position_y", 0)
                other_dist_to_int = math.sqrt((ox - int_x) ** 2 + (oy - int_y) ** 2)

                if other_dist_to_int < 80.0:
                    if other_dist_to_int < dist_to_int and dist_to_int > 30.0:
                        # Zipper Merge Anti-deadlock
                        if (
                            other_data.get("speed", 0) < 1.0
                            and self.agent_id > other_id
                        ):
                            continue
                        conflict_merge = True
                        break

            if conflict_merge:
                self._brake("Zipper Merge: Yielding")
                return

        self._recover_speed()



    def _brake(self, reason):
        self.current_state = "BRAKING"
        self.turn_intent = "YIELDING"
        self.speed = max(0.0, self.speed - 3.0)

    def _recover_speed(self):
        self.current_state = "CRUISE"
        if self.speed < self.desired_speed:
            self.speed += 1.0
        elif self.speed > self.desired_speed:
            self.speed -= 1.0

    def get_emergency_status(self):
        data = {
            "agent_id": self.agent_id,
            "vehicle_type": self.vehicle_type,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "speed": self.speed,
            "heading": self.heading,
            "visual_angle": self.visual_angle,
            "intent": self.current_state,
            "driving_style": self.driving_style,
            "target_int": self.target_int,
            "is_crashed": self.is_crashed,
            "target_lane_offset": self.target_lane_offset,
            "timestamp": time.time(),
        }
        data["signature"] = SecurityManager.sign_data(data)
        return data

    def has_decided_to_brake(self):
        return self.current_state == "BRAKING"
