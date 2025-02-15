#from fetchai.ledger.api import LedgerApi
#from fetchai.ledger.crypto import Entity, Address
#from fetchai.ledger.contract import Contract


import random


class FetchAgent:
    def __init__(self, name, base_consumption=0, base_production=0):
        self.name = name
        self.base_consumption = base_consumption
        self.base_production = base_production
        self.ct_balance = 0

    def consume_energy(self):
        return self.base_consumption + random.uniform(-0.2, 0.2) * self.base_consumption

    def produce_energy(self, weather_factor=1.0):
        return self.base_production * weather_factor + random.uniform(-0.1, 0.1) * self.base_production

    def interact_with_grid(self, energy):
        pass

    def update_state(self):
        pass

    def __str__(self):
        return f"FetchAgent(name={self.name}, energy_consumption={self.base_consumption}, energy_production={self.base_production}, ct_balance={self.ct_balance})"

class Consumer(FetchAgent):
    def __init__(self, id, base_consumption):
        super().__init__(id, base_consumption)

class Prosumer(FetchAgent):
    def __init__(self, id, base_consumption, base_production):
        super().__init__(id, base_consumption, base_production)

class Producer(FetchAgent):
    def __init__(self, id, base_production):
        super().__init__(id, base_production=base_production)