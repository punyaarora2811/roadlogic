import math
import threading
import time

from v2x_security import SecurityManager

class TrafficLightAgent:
    def __init__(self, broker, agent_id="Center_TrafficLight"):
        self.broker = broker
        self.agent_id = agent_id
        self.state_NS = "GREEN"  # North-South Axis
        self.state_EW = "RED"  # East-West Axis
        self.running = True
    def start(self):
        """Start the traffic light on a separate thread to avoid blocking the GUI."""
        threading.Thread(target=self._run_loop, daemon=True).start()
    def _run_loop(self):
        while self.running:
            if not getattr(self.broker, "infrastructure_active", True):
                self._publish_state(
                    "YELLOW_BLINKING", "YELLOW_BLINKING", time_to_change=0.0
                )
                time.sleep(0.5)  # -> frequent to detect restart
                continue
            traffic_data = self.broker.receive(self.agent_id)
            emergency_heading = None
            for v_id, v_data in traffic_data.items():
                if v_data.get("vehicle_type") == "Ambulance":  # ambulance
                    dist_to_center = math.sqrt(
                        (400 - v_data.get("position_x", 0)) ** 2
                        + (400 - v_data.get("position_y", 0)) ** 2
                    )
                    if dist_to_center < 300:  # close to intersection
                        emergency_heading = v_data.get("heading")
                        break
            # EMERGENCY: Ambulance forces color
            if emergency_heading:
                if emergency_heading in ["NORTH", "SOUTH"]:
                    self._publish_state(
                        "GREEN", "RED", time_to_change=99.0
                    )
                else:
                    self._publish_state("RED", "GREEN", time_to_change=99.0)
                time.sleep(0.1)
                continue
            # NORMAL CYCLE
            # NS Green, EW Red (5 seconds)
            if not self._wait_interruptible(5.0, "GREEN", "RED"):
                continue
            # NS Yellow, EW Red (2 seconds)
            if not self._wait_interruptible(2.0, "YELLOW", "RED"):
                continue
            # NS Red, EW Green (5 seconds)
            if not self._wait_interruptible(5.0, "RED", "GREEN"):
                continue
            # NS Red, EW Yellow (2 seconds)
            if not self._wait_interruptible(2.0, "RED", "YELLOW"):
                continue

    def _wait_interruptible(self, duration, state_ns, state_ew):
        """Wait a specific time, but publish the countdown for cars (GLOSA)."""
        steps = int(duration / 0.1)
        for step in range(steps):
            if not getattr(self.broker, "infrastructure_active", True):
                return False
            # CALCULATE REMAINING TIME: total steps - steps taken
            time_to_change = (steps - step) * 0.1
            # Publish state every 0.1 seconds, along with remaining time
            self._publish_state(state_ns, state_ew, time_to_change)
            time.sleep(0.1)
        return True

    def _publish_state(self, ns, ew, time_to_change):
        """Send current state to all cars in the network."""
        self.state_NS = ns
        self.state_EW = ew
        data_package = {
            "agent_id": self.agent_id,
            "vehicle_type": "Infrastructure",
            "state_NS": self.state_NS,
            "state_EW": self.state_EW,
            "time_to_change": round(time_to_change, 1),
            "position_x": 400,
            "position_y": 400,
            "timestamp": time.time(),
        }
        # Digitally sign the traffic light state to prevent data tampering
        data_package["signature"] = SecurityManager.sign_data(data_package)
        self.broker.publish(self.agent_id, data_package)
