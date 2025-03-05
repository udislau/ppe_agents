class EnergyStorage:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity
        self.current_level = 0

    def charge(self, amount):
        available_capacity = self.capacity - self.current_level
        charged_amount = min(amount, available_capacity)
        self.current_level += charged_amount
        return charged_amount

    def discharge(self, amount):
        discharged_amount = min(amount, self.current_level)
        self.current_level -= discharged_amount
        return discharged_amount