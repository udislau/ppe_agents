class EnergyStorage:
    def __init__(self, id, capacity, charge_efficiency=0.95, discharge_efficiency=0.95):
        self.id = id
        self.capacity = capacity
        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency
        self.current_level = 0

    def charge(self, energy):
        effective_energy = energy * self.charge_efficiency
        available_space = self.capacity - self.current_level
        energy_charged = min(effective_energy, available_space)
        self.current_level += energy_charged
        return energy_charged

    def discharge(self, energy):
        energy_available = self.current_level * self.discharge_efficiency
        energy_discharged = min(energy, energy_available)
        self.current_level -= energy_discharged / self.discharge_efficiency
        return energy_discharged