import threading


class V2XBroker:
    def __init__(self):
        self.vehicles_status = {}
        self.lock = threading.Lock()
        self.infrastructure_active = True
        self.ai_enabled = True

    def publish(self, vehicle_id: str, data_package: dict):
        with self.lock:
            self.vehicles_status[vehicle_id] = data_package

    def receive(self, requesting_vehicle_id: str) -> dict:
        with self.lock:
            return {
                v_id: data
                for v_id, data in self.vehicles_status.items()
                if v_id != requesting_vehicle_id
            }
