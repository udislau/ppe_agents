import random

class EnergySource:
    def __init__(self, name, capacity):
        self.name = name
        self.capacity = capacity

    def generate_energy(self):
        return random.randint(0, self.capacity)  # Example generation logic