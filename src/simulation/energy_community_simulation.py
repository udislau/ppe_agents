import random
from models.cooperative import Cooperative

# --- Przykładowa konfiguracja i uruchomienie symulacji ---

if __name__ == "__main__":
    config = {
        'consumers': [
            {'id': 'C1', 'base_consumption': 6},
            {'id': 'C2', 'base_consumption': 8},
            {'id': 'C3', 'base_consumption': 9},
        ],
        'prosumers': [
            {'id': 'P1', 'base_consumption': 5, 'base_production': 3},
            {'id': 'P2', 'base_consumption': 6, 'base_production': 2},
        ],
        'producers': [
            {'id': 'PV1', 'base_production': 50},
        ],
        'storage': {'id': 'S1', 'capacity': 120}
    }
    
    cooperative = Cooperative(config, initial_token_balance=100)
    
    steps = 48
    weather_profile = [random.uniform(0.5, 1.0) for _ in range(steps)]
    
    p2p_base_price = 0.5
    grid_price = 1.0
    min_price = 0.2
    token_mint_rate = 0.1
    token_burn_rate = 0.1
    
    demand_supply_pattern = {
        'day': {'consumption': 1.0, 'production': 1.0},
        'night': {'consumption': 0.5, 'production': 0.0},
        'high_demand': {'consumption': 1.2, 'production': 1.0},
        'low_demand': {'consumption': 0.7, 'production': 1.0},
        'high_supply': {'consumption': 1.0, 'production': 1.2},
        'low_supply': {'consumption': 1.0, 'production': 0.8},
    }
    
    cooperative.simulate(steps, weather_profile, p2p_base_price, 
                         grid_price, min_price, token_mint_rate, token_burn_rate, demand_supply_pattern)
    cooperative.plot_results(p2p_base_price, grid_price, token_mint_rate, token_burn_rate)
