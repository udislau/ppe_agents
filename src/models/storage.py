class Storage:
    def __init__(self, id, capacity, current_charge=0):
        self.name = id
        self.capacity = capacity
        self.current_charge = current_charge

    def charge(self, amount):
        available_capacity = self.capacity - self.current_charge
        charged = min(amount, available_capacity)
        self.current_charge += charged
        return charged

    def discharge(self, amount):
        discharged = min(amount, self.current_charge)
        self.current_charge -= discharged
        return discharged
