# animal_obstacle.py
import time
import random

class AnimalObstacle:
    def __init__(self, x, y):
        self.agent_id = "Deer"
        self.start_x = x
        self.start_y = y
        self.position_x = x
        self.position_y = y
        self.speed = 30.0
        self.state = "HIDDEN"
        # Autonomous crossing timer: first crossing in 20-40 s after startup
        self._next_trigger = time.time() + random.uniform(20.0, 40.0)

    def update(self, dt):
        now = time.time()
        if self.state == "CROSSING":
            self.position_y += self.speed * dt
            if self.position_y > 730:
                self.state = "HIDDEN"
                # Reset timer for the next autonomous crossing
                self._next_trigger = now + random.uniform(20.0, 40.0)
                print("[Deer] Crossed road — next autonomous crossing scheduled.")
        elif self.state == "HIDDEN":
            # Autonomous trigger: cross when timer fires
            if now >= self._next_trigger:
                self.position_x = self.start_x
                self.position_y = self.start_y
                self.state = "CROSSING"
                print("[Deer] Autonomous crossing triggered!")
        elif self.state == "CRASHED":
            # After a crash, reset and schedule the next crossing
            if now >= self._next_trigger:
                self.position_x = self.start_x
                self.position_y = self.start_y
                self.state = "HIDDEN"
                self._next_trigger = now + random.uniform(20.0, 40.0)

    def get_status(self):
        if self.state in ["CROSSING", "CRASHED"]:
            return {
                "agent_id": self.agent_id,
                "position_x": self.position_x,
                "position_y": self.position_y,
                "speed": self.speed if self.state != "CRASHED" else 0.0,
                "vehicle_type": "Animal",
                "heading": "CROSSING",
                "intent": "JUMPING",
                "is_crashed": self.state
                == "CRASHED",
            }
        return None
