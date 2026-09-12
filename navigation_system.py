import math
import networkx as nx
from map_config import nodes, edges


class Navigator:
    def __init__(self, agent_id, start_node, target_node):
        self.agent_id = agent_id
        self.target_lane_offset = 0.0
        self.current_lane_offset = 0.0

        # 1. ROUTE GENERATION
        self.graph = nx.DiGraph()
        for start, end, cost in edges:
            self.graph.add_edge(start, end, weight=cost)

        try:
            self.route = nx.shortest_path(
                self.graph, source=start_node, target=target_node, weight="weight"
            )
        except nx.NetworkXNoPath:
            print(
                f"[{self.agent_id}] ERROR: No path from {start_node} to {target_node}!"
            )
            self.route = [start_node]

        self.current_node_index = 0

        # 2. SET INITIAL COORDINATES
        start_coords = nodes[self.route[0]]
        self.base_x = start_coords[0]
        self.base_y = start_coords[1]
        self.position_x = self.base_x
        self.position_y = self.base_y

        self.visual_angle = 0.0
        self.heading = "EAST"
        self.turn_intent = "GO_STRAIGHT"

        self._initialize_heading()
        self._update_heading_and_turn()

    def _initialize_heading(self):
        """Sets the initial orientation based on the first two nodes in the route."""
        if len(self.route) > 1:
            next_coords = nodes[self.route[1]]
            angle = math.atan2(
                next_coords[1] - self.position_y, next_coords[0] - self.position_x
            )
            self._set_heading_from_degrees(math.degrees(angle))

    def _set_heading_from_degrees(self, deg):
        """Transforms the angle into cardinal directions."""
        if -45 <= deg <= 45:
            self.heading = "EAST"
        elif 45 < deg <= 135:
            self.heading = "SOUTH"
        elif -135 <= deg < -45:
            self.heading = "NORTH"
        else:
            self.heading = "WEST"

    def _update_heading_and_turn(self):
        """Calculates the signaling intention of the car."""
        idx = self.current_node_index
        if idx < len(self.route) - 2:
            p_curr = nodes[self.route[idx]]
            p_next = nodes[self.route[idx + 1]]
            p_next2 = nodes[self.route[idx + 2]]

            angle1 = math.atan2(p_next[1] - p_curr[1], p_next[0] - p_curr[0])
            angle2 = math.atan2(p_next2[1] - p_next[1], p_next2[0] - p_next[0])
            diff = math.degrees(angle2 - angle1)

            while diff <= -180:
                diff += 360
            while diff > 180:
                diff -= 360

            if -45 < diff < 45:
                self.turn_intent = "GO_STRAIGHT"
            elif diff <= -45:
                self.turn_intent = "TURN_LEFT"
            elif diff >= 45:
                self.turn_intent = "TURN_RIGHT"
        else:
            self.turn_intent = "GO_STRAIGHT"

    def update_position(self, dt, speed):
        """Moves the car to the next node."""
        if speed <= 0:
            return

        if self.current_node_index >= len(self.route) - 1:
            # Continues straight if it reached the end (goes off screen)
            angle_rad = math.radians(self.visual_angle)
            self.base_x += speed * dt * math.cos(angle_rad)
            self.base_y += speed * dt * math.sin(angle_rad)
        else:
            next_node_name = self.route[self.current_node_index + 1]
            tx, ty = nodes[next_node_name]
            dist = math.sqrt((tx - self.base_x) ** 2 + (ty - self.base_y) ** 2)

            if dist < 5.0:
                self.current_node_index += 1
                if self.current_node_index < len(self.route) - 1:
                    self._update_heading_and_turn()
                    tx, ty = nodes[self.route[self.current_node_index + 1]]

            if self.current_node_index < len(self.route) - 1:
                angle_rad = math.atan2(ty - self.base_y, tx - self.base_x)
                self.visual_angle = math.degrees(angle_rad)
                self.base_x += speed * dt * math.cos(angle_rad)
                self.base_y += speed * dt * math.sin(angle_rad)

        self._set_heading_from_degrees(self.visual_angle)

        # Lane change logic (Waze Avoidance)
        steer_speed = 55.0
        if self.current_lane_offset < self.target_lane_offset:
            self.current_lane_offset = min(
                self.current_lane_offset + steer_speed * dt, self.target_lane_offset
            )
        elif self.current_lane_offset > self.target_lane_offset:
            self.current_lane_offset = max(
                self.current_lane_offset - steer_speed * dt, self.target_lane_offset
            )

        angle_rad = math.radians(self.visual_angle)
        perp_angle = angle_rad - math.pi / 2

        self.position_x = self.base_x + math.cos(perp_angle) * self.current_lane_offset
        self.position_y = self.base_y + math.sin(perp_angle) * self.current_lane_offset
