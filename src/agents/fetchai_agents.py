import random

class Consumer:
    def __init__(self, id, base_consumption):
        self.name = id
        self.base_consumption = base_consumption

    def consume_energy(self):
        return self.base_consumption

class Prosumer(Consumer):
    def __init__(self, id, base_consumption, base_production):
        super().__init__(id, base_consumption)
        self.base_production = base_production

    def produce_energy(self, weather_factor):
        return self.base_production * weather_factor + random.uniform(-0.1, 0.1) * self.base_production

class Producer:
    def __init__(self, id, base_production):
        self.name = id
        self.base_production = base_production

    def produce_energy(self, weather_factor):
        return self.base_production * weather_factor + random.uniform(-0.1, 0.1) * self.base_production

class Storage:
    def __init__(self, id, capacity):
        self.name = id
        self.capacity = capacity
        self.current_level = 0

    def charge(self, amount):
        available_capacity = self.capacity - self.current_level
        charged = min(amount, available_capacity)
        self.current_level += charged
        return charged

    def discharge(self, amount):
        discharged = min(amount, self.current_level)
        self.current_level -= discharged
        return discharged