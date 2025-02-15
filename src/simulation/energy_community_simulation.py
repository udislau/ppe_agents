import random
import matplotlib.pyplot as plt
from agents.fetchai_agents import FetchAgent
import datetime

# --- Definicje agentów ---

class Consumer(FetchAgent):
    def __init__(self, id, base_consumption):
        super().__init__(id, base_consumption)

class Prosumer(FetchAgent):
    def __init__(self, id, base_consumption, base_production):
        super().__init__(id, base_consumption, base_production)

class Producer(FetchAgent):
    def __init__(self, id, base_production):
        super().__init__(id, base_production=base_production)

class EnergyStorage:
    """
    Magazyn energii – umożliwia ładowanie nadwyżki energii oraz rozładowanie w przypadku niedoborów.
    """
    def __init__(self, id, capacity, charge_efficiency=0.95, discharge_efficiency=0.95):
        self.id = id
        self.capacity = capacity
        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency
        self.current_level = 0  # zgromadzona energia (kWh)

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

# --- Spółdzielnia energetyczna z rozszerzoną logiką negocjacji, tokenów oraz gamifikacji ---

class Cooperative:
    def __init__(self, config, initial_token_balance=100):
        """
        Konfiguracja spółdzielni:
        config = {
            'consumers': [{'id': 'C1', 'base_consumption': ...}, ...],
            'prosumers': [{'id': 'P1', 'base_consumption': ..., 'base_production': ...}, ...],
            'producers': [{'id': 'PV1', 'base_production': ...}, ...],
            'storage': {'id': 'S1', 'capacity': ...}
        }
        """
        self.consumers = [Consumer(**c) for c in config.get('consumers', [])]
        self.prosumers = [Prosumer(**p) for p in config.get('prosumers', [])]
        self.producers = [Producer(**p) for p in config.get('producers', [])]
        storage_config = config.get('storage', None)
        self.storage = EnergyStorage(**storage_config) if storage_config else None

        # Historia symulacji
        self.history_consumption = []
        self.history_production = []
        self.history_traded_energy = []
        self.history_grid_purchase = []
        self.history_storage = []
        self.history_avg_trade_price = []
        self.history_token_reward = []  # łączna liczba tokenów przyznanych w danym kroku
        self.history_grid_penalty = []  # tokeny spalane za energię z gridu

        # Inicjalizacja tokenów dla agentów
        self.token_balances = {}
        for agent in self.consumers + self.prosumers + self.producers:
            self.token_balances[agent.name] = initial_token_balance
        # Inicjalizacja tokenów dla magazynu energii
        if self.storage:
            self.token_balances[self.storage.id] = initial_token_balance
        # Fundusz spółdzielni
        self.community_token_balance = initial_token_balance

        # Dla gamifikacji – osiągnięcia (próg tokenów)
        self.achievements = {}  # dict: id agenta -> lista osiągnięć

    def update_achievements(self, agent_id):
        """Sprawdza, czy agent przekroczył nowe progi tokenowe i wypisuje komunikat."""
        thresholds = [150, 200, 250, 300]
        current = self.token_balances[agent_id]
        achieved = self.achievements.get(agent_id, [])
        for thr in thresholds:
            if current >= thr and thr not in achieved:
                print(f"Agent {agent_id} zdobył osiągnięcie: przekroczono {thr} CT!")
                achieved.append(thr)
        self.achievements[agent_id] = achieved

    def print_leaderboard(self):
        """Wyświetla ranking agentów według salda tokenowego."""
        sorted_agents = sorted(self.token_balances.items(), key=lambda x: x[1], reverse=True)
        print("=== Leaderboard CT ===")
        for rank, (agent_id, tokens) in enumerate(sorted_agents, 1):
            print(f"{rank}. {agent_id}: {tokens:.2f} CT")
        print("======================")

    def simulate_step_with_negotiation(self, weather_factor, p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, time_of_day, demand_supply_pattern):
        buyer_offers = []
        seller_offers = []

        total_consumption = 0
        total_production = 0

        # Adjust consumption and production based on time of day and demand/supply pattern
        consumption_factor = demand_supply_pattern.get(time_of_day, {}).get('consumption', 1.0)
        production_factor = demand_supply_pattern.get(time_of_day, {}).get('production', 1.0)

        # Oferty konsumentów (kupno)
        for consumer in self.consumers:
            consumption = consumer.consume_energy() * consumption_factor
            total_consumption += consumption
            buyer_price = p2p_base_price * 1.2  # kupujący skłonni zapłacić premię
            buyer_offers.append({'id': consumer.name, 'quantity': consumption, 'price': buyer_price})

        # Oferty prosumentów – mogą być kupującymi lub sprzedającymi
        for prosumer in self.prosumers:
            consumption = prosumer.consume_energy() * consumption_factor
            production = prosumer.produce_energy(weather_factor) * production_factor
            total_consumption += consumption
            total_production += production
            net = production - consumption
            if net > 0:
                seller_price = p2p_base_price * 0.8
                seller_offers.append({'id': prosumer.name, 'quantity': net, 'price': seller_price})
            elif net < 0:
                buyer_price = p2p_base_price * 1.2
                buyer_offers.append({'id': prosumer.name, 'quantity': -net, 'price': buyer_price})

        # Oferty producentów – tylko sprzedaż
        for producer in self.producers:
            production = producer.produce_energy(weather_factor) * production_factor
            total_production += production
            seller_price = p2p_base_price * 0.75
            seller_offers.append({'id': producer.name, 'quantity': production, 'price': seller_price})

        # Sortowanie ofert: kupujący wg malejącej ceny, sprzedający wg rosnącej ceny
        buyer_offers.sort(key=lambda x: x['price'], reverse=True)
        seller_offers.sort(key=lambda x: x['price'])

        # Proces negocjacji – dopasowywanie ofert
        trades = []
        total_traded_energy = 0
        total_trade_value = 0
        token_rewards_this_step = 0  # suma tokenów przyznanych w bieżącym kroku
        storage_discharge = 0
        storage_charge = 0

        i, j = 0, 0
        while i < len(buyer_offers) and j < len(seller_offers):
            buyer = buyer_offers[i]
            seller = seller_offers[j]
            if buyer['price'] >= seller['price']:
                trade_qty = min(buyer['quantity'], seller['quantity'])
                trade_price = (buyer['price'] + seller['price']) / 2
                trades.append({'buyer': buyer['id'], 'seller': seller['id'], 'quantity': trade_qty, 'price': trade_price})
                total_traded_energy += trade_qty
                total_trade_value += trade_qty * trade_price

                # Aktualizacja ofert
                buyer['quantity'] -= trade_qty
                seller['quantity'] -= trade_qty

                # Przyznanie tokenów za energię z OZE (minting) – energia handlowana lokalnie
                # Za każdy kWh handlowany, kupujący i sprzedający otrzymują tokeny,
                # a część trafia do funduszu spółdzielni.
                minted = trade_qty * token_mint_rate
                buyer_reward = minted / 2
                seller_reward = minted / 2
                community_bonus = minted * 0.1  # dodatkowy bonus dla spółdzielni

                self.token_balances[buyer['id']] += buyer_reward
                self.token_balances[seller['id']] += seller_reward
                self.community_token_balance += community_bonus
                token_rewards_this_step += (buyer_reward + seller_reward + community_bonus)

                # Aktualizacja osiągnięć
                self.update_achievements(buyer['id'])
                self.update_achievements(seller['id'])

                if abs(buyer['quantity']) < 1e-6:
                    i += 1
                if abs(seller['quantity']) < 1e-6:
                    j += 1
            else:
                break

        avg_trade_price = total_trade_value / total_traded_energy if total_traded_energy > 0 else 0

        # Pozostały niezrealizowany popyt
        residual_demand = sum(offer['quantity'] for offer in buyer_offers[i:]) if i < len(buyer_offers) else 0

        # Include energy storage in the trading offers if there is residual demand
        if self.storage and residual_demand > 0:
            storage_discharge = self.storage.discharge(residual_demand)
            if storage_discharge > 0:
                seller_price = p2p_base_price * 0.85
                seller_offers.append({'id': self.storage.id, 'quantity': storage_discharge, 'price': seller_price})
                seller_offers.sort(key=lambda x: x['price'])

                # Re-run the trading process with the updated seller offers
                while i < len(buyer_offers) and j < len(seller_offers):
                    buyer = buyer_offers[i]
                    seller = seller_offers[j]
                    if buyer['price'] >= seller['price']:
                        trade_qty = min(buyer['quantity'], seller['quantity'])
                        trade_price = (buyer['price'] + seller['price']) / 2
                        trades.append({'buyer': buyer['id'], 'seller': seller['id'], 'quantity': trade_qty, 'price': trade_price})
                        total_traded_energy += trade_qty
                        total_trade_value += trade_qty * trade_price

                        # Aktualizacja ofert
                        buyer['quantity'] -= trade_qty
                        seller['quantity'] -= trade_qty

                        # Przyznanie tokenów za energię z OZE (minting) – energia handlowana lokalnie
                        # Za każdy kWh handlowany, kupujący i sprzedający otrzymują tokeny,
                        # a część trafia do funduszu spółdzielni.
                        minted = trade_qty * token_mint_rate
                        buyer_reward = minted / 2
                        seller_reward = minted / 2
                        community_bonus = minted * 0.1  # dodatkowy bonus dla spółdzielni

                        self.token_balances[buyer['id']] += buyer_reward
                        self.token_balances[seller['id']] += seller_reward
                        self.community_token_balance += community_bonus
                        token_rewards_this_step += (buyer_reward + seller_reward + community_bonus)

                        # Aktualizacja osiągnięć
                        self.update_achievements(buyer['id'])
                        self.update_achievements(seller['id'])

                        if abs(buyer['quantity']) < 1e-6:
                            i += 1
                        if abs(seller['quantity']) < 1e-6:
                            j += 1
                    else:
                        break
                # Jaka była średnia cena energii z magazynu?
                avg_trade_price = total_trade_value / total_traded_energy if total_traded_energy > 0 else 0

        # Pozostały niezrealizowany popyt i nadwyżka
        residual_demand = sum(offer['quantity'] for offer in buyer_offers[i:]) if i < len(buyer_offers) else 0
        residual_surplus = sum(offer['quantity'] for offer in seller_offers[j:]) if j < len(seller_offers) else 0

        # Interwencja magazynu – najpierw magazynujemy nadwyżkę
        if self.storage and residual_surplus > 0:
            charged = self.storage.charge(residual_surplus)
            storage_charge = charged
            residual_surplus -= charged

        # Uzupełnienie niedoboru – zakup energii z gridu
        grid_purchase = residual_demand
        grid_cost = grid_purchase * grid_price

        # Mechanizm spalania tokenów: jeśli energia pochodzi z gridu, spalamy tokeny
        burned_tokens = grid_purchase * token_burn_rate
        # W tym przykładzie odejmujemy spalone tokeny od funduszu spółdzielni
        self.community_token_balance = max(self.community_token_balance - burned_tokens, 0)

        # Podsumowanie bieżącego kroku
        print("=== Negocjacje w bieżącym kroku ===")
        print(f"Łączne zużycie: {total_consumption:.2f} kWh")
        print(f"Łączna produkcja: {total_production:.2f} kWh")
        print(f"Rozładowanie magazynu: {storage_discharge:.2f} kWh")
        if self.storage:
            print(f"Doładowanie magazynu: {storage_charge:.2f} kWh")
            print(f"Stan magazynu po interwencji: {self.storage.current_level:.2f} kWh")
        print(f"Handlowana energia (OZE): {total_traded_energy:.2f} kWh, średnia cena: {avg_trade_price:.2f} PLN/kWh")
        print(f"Tokeny mintowane w tym kroku: {token_rewards_this_step:.2f}")
        if grid_purchase > 0:
            print(f"Niedobór energii: {grid_purchase:.2f} kWh, zakupione z gridu po {grid_price:.2f} PLN/kWh (koszt: {grid_cost:.2f} PLN)")
            print(f"Tokeny spalane z powodu gridu: {burned_tokens:.2f}")
        else:
            print("Brak zakupu energii z gridu.")
        print("Salda tokenów:")
        for agent_id, balance in self.token_balances.items():
            print(f"  {agent_id}: {balance:.2f} CT")
        print(f"Fundusz spółdzielni: {self.community_token_balance:.2f} CT")
        self.print_leaderboard()
        print("=" * 50)

        # Zapis wyników bieżącego kroku
        self.history_consumption.append(total_consumption)
        self.history_production.append(total_production)
        self.history_traded_energy.append(total_traded_energy)
        self.history_grid_purchase.append(grid_purchase)
        self.history_storage.append(self.storage.current_level if self.storage else None)
        self.history_avg_trade_price.append(avg_trade_price)
        self.history_token_reward.append(token_rewards_this_step)
        self.history_grid_penalty.append(burned_tokens)

    def simulate(self, steps, weather_profile, p2p_base_price=0.5, grid_price=1.0, min_price=0.2, token_mint_rate=0.05, token_burn_rate=0.1, demand_supply_pattern=None):
        if demand_supply_pattern is None:
            demand_supply_pattern = {
                'day': {'consumption': 1.0, 'production': 1.0},
                'night': {'consumption': 0.8, 'production': 0.5},
                'high_demand': {'consumption': 1.2, 'production': 1.0},
                'low_demand': {'consumption': 0.7, 'production': 1.0},
                'high_supply': {'consumption': 1.0, 'production': 1.2},
                'low_supply': {'consumption': 1.0, 'production': 0.8},
            }

        for step in range(steps):
            time_of_day = 'day' if 6 <= step % 24 < 20 else 'night'
            self.simulate_step_with_negotiation(weather_profile[step], p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, time_of_day, demand_supply_pattern)

    def plot_results(self, p2p_base_price, grid_price, token_mint_rate, token_burn_rate):
        steps = range(len(self.history_consumption))
        plt.figure(figsize=(14, 16))
        
        plt.subplot(6, 1, 1)
        plt.plot(steps, self.history_consumption, label="Zużycie")
        plt.plot(steps, self.history_production, label="Produkcja")
        plt.ylabel("Energia (kWh)")
        plt.title("Zużycie vs Produkcja")
        plt.legend()
        plt.grid(True)
        
        plt.subplot(6, 1, 2)
        plt.plot(steps, self.history_traded_energy, label="Energia sprzedana (OZE)")
        plt.plot(steps, self.history_grid_purchase, label="Zakup z gridu (kWh)")
        plt.ylabel("Energia (kWh)")
        plt.title("Negocjacje i zakup z gridu")
        plt.legend()
        plt.grid(True)
        
        plt.subplot(6, 1, 3)
        plt.plot(steps, self.history_avg_trade_price, label="Średnia cena (PLN/kWh)")
        plt.ylabel("Cena (PLN/kWh)")
        plt.title("Cena negocjacji")
        plt.legend()
        plt.grid(True)
        
        plt.subplot(6, 1, 4)
        plt.plot(steps, self.history_token_reward, label="Tokeny mintowane")
        plt.ylabel("Tokeny")
        plt.title("Przyznawanie tokenów (OZE)")
        plt.legend()
        plt.grid(True)
        
        plt.subplot(6, 1, 5)
        plt.plot(steps, self.history_grid_penalty, label="Tokeny spalane")
        plt.ylabel("Tokeny")
        plt.xlabel("Krok czasowy")
        plt.title("Spalanie tokenów (grid)")
        plt.legend()
        plt.grid(True)
        
        plt.subplot(6, 1, 6)
        plt.plot(steps, self.history_storage, label="Stan magazynu")
        plt.ylabel("Energia (kWh)")
        plt.xlabel("Krok czasowy")
        plt.title("Stan magazynu energii")
        plt.legend()
        plt.grid(True)
        
        # Add simulation parameters and date/time to the plot
        now = datetime.datetime.now()
        date_time_str = now.strftime("%Y-%m-%d_%H-%M-%S")
        plt.suptitle(f"Simulation Parameters: P2P Base Price={p2p_base_price}, Grid Price={grid_price}, Token Mint Rate={token_mint_rate}, Token Burn Rate={token_burn_rate}\nDate and Time: {now.strftime('%Y-%m-%d %H:%M:%S')}", fontsize=14, y=0.98)

        # Adjust layout to accommodate the title
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        # Save the image with date and time in the file name
        file_name = f"output/energy_simulation_{date_time_str}.png"
        plt.savefig(file_name)
        plt.close()

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
    token_mint_rate = 0.05
    token_burn_rate = 0.1
    
    demand_supply_pattern = {
        'day': {'consumption': 1.0, 'production': 1.0},
        'night': {'consumption': 0.5, 'production': 0.0},
        'high_demand': {'consumption': 1.2, 'production': 1.0},
        'low_demand': {'consumption': 0.7, 'production': 1.0},
        'high_supply': {'consumption': 1.0, 'production': 1.2},
        'low_supply': {'consumption': 1.0, 'production': 0.8},
    }
    
    cooperative.simulate(steps, weather_profile, p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, demand_supply_pattern)
    cooperative.plot_results(p2p_base_price, grid_price, token_mint_rate, token_burn_rate)
