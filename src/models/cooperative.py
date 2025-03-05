import matplotlib.pyplot as plt
import datetime
from agents.fetchai_agents import Storage

# Definicja progów
thresholds = [10, 50, 100, 500, 1000]

class Cooperative:
    def __init__(self, config, initial_token_balance):
        self.storage = Storage(**config['storage']) if 'storage' in config else None
        self.token_balances = {'community': initial_token_balance}
        if self.storage:
            self.token_balances[self.storage.name] = initial_token_balance
        self.community_token_balance = initial_token_balance
        self.achievements = {}
        self.history_consumption = []
        self.history_production = []
        self.history_traded_energy = []
        self.history_grid_purchase = []
        self.history_storage = []
        self.history_avg_trade_price = []
        self.history_token_reward = []
        self.history_grid_penalty = []
        self.history_token_balance = []
        self.history_p2p_price = []
        self.history_grid_price = []

    def update_achievements(self, agent_id):
        current = self.token_balances[agent_id]
        achieved = self.achievements.get(agent_id, [])
        for thr in thresholds:
            if current >= thr and thr not in achieved:
                print(f"Agent {agent_id} zdobył osiągnięcie: przekroczono {thr} CT!")
                achieved.append(thr)
        self.achievements[agent_id] = achieved

    def print_leaderboard(self):
        sorted_agents = sorted(self.token_balances.items(), key=lambda x: x[1], reverse=True)
        print("=== Leaderboard CT ===")
        for rank, (agent_id, tokens) in enumerate(sorted_agents, 1):
            print(f"{rank}. {agent_id}: {tokens:.2f} CT")
        print("======================")

    def simulate_step_with_negotiation(self, step, p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, hourly_data):
        # Pobierz dane godzinowe dla bieżącego kroku
        hourly_data_step = hourly_data[step]
        consumption_factor = hourly_data_step['consumption']
        production_factor = hourly_data_step['production']

        buyer_offers = []
        seller_offers = []

        total_consumption = consumption_factor
        total_production = production_factor

        buyer_price = p2p_base_price * 1.2
        buyer_offers.append({'id': 'community', 'quantity': total_consumption, 'price': buyer_price})

        seller_price = p2p_base_price * 0.8
        seller_offers.append({'id': 'community', 'quantity': total_production, 'price': seller_price})

        buyer_offers.sort(key=lambda x: x['price'], reverse=True)
        seller_offers.sort(key=lambda x: x['price'])

        trades = []
        total_traded_energy = 0
        total_trade_value = 0
        token_rewards_this_step = 0

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

                buyer['quantity'] -= trade_qty
                seller['quantity'] -= trade_qty

                minted = trade_qty * token_mint_rate
                buyer_reward = minted / 2
                seller_reward = minted / 2
                community_bonus = minted * 0.1

                self.token_balances[buyer['id']] += buyer_reward
                self.token_balances[seller['id']] += seller_reward
                self.community_token_balance += community_bonus
                token_rewards_this_step += (buyer_reward + seller_reward + community_bonus)

                self.update_achievements(buyer['id'])
                self.update_achievements(seller['id'])

                if abs(buyer['quantity']) < 1e-6:
                    i += 1
                if abs(seller['quantity']) < 1e-6:
                    j += 1
            else:
                break

        avg_trade_price = total_trade_value / total_traded_energy if total_traded_energy > 0 else 0

        residual_demand = sum(offer['quantity'] for offer in buyer_offers[i:]) if i < len(buyer_offers) else 0
        residual_surplus = sum(offer['quantity'] for offer in seller_offers[j:]) if j < len(seller_offers) else 0

        if self.storage and residual_surplus > 0:
            charged = self.storage.charge(residual_surplus)
            residual_surplus -= charged

        if self.storage and residual_demand > 0:
            storage_discharge = self.storage.discharge(residual_demand)
            if storage_discharge > 0:
                seller_price = p2p_base_price * 0.85
                seller_offers.append({'id': self.storage.name, 'quantity': storage_discharge, 'price': seller_price})
                seller_offers.sort(key=lambda x: x['price'])

                while i < len(buyer_offers) and j < len(seller_offers):
                    buyer = buyer_offers[i]
                    seller = seller_offers[j]
                    if buyer['price'] >= seller['price']:
                        trade_qty = min(buyer['quantity'], seller['quantity'])
                        trade_price = (buyer['price'] + seller['price']) / 2
                        trades.append({'buyer': buyer['id'], 'seller': seller['id'], 'quantity': trade_qty, 'price': trade_price})
                        total_traded_energy += trade_qty
                        total_trade_value += trade_qty * trade_price

                        buyer['quantity'] -= trade_qty
                        seller['quantity'] -= trade_qty

                        minted = trade_qty * token_mint_rate
                        buyer_reward = minted / 2
                        seller_reward = minted / 2
                        community_bonus = minted * 0.1

                        self.token_balances[buyer['id']] += buyer_reward
                        self.token_balances[seller['id']] += seller_reward
                        self.community_token_balance += community_bonus
                        token_rewards_this_step += (buyer_reward + seller_reward + community_bonus)

                        self.update_achievements(buyer['id'])
                        self.update_achievements(seller['id'])

                        if abs(buyer['quantity']) < 1e-6:
                            i += 1
                        if abs(seller['quantity']) < 1e-6:
                            j += 1
                    else:
                        break

        grid_purchase = residual_demand
        grid_cost = grid_purchase * grid_price

        burned_tokens = grid_purchase * token_burn_rate
        self.community_token_balance = max(self.community_token_balance - burned_tokens, 0)

        print("=== Negocjacje w bieżącym kroku ===")
        print(f"Łączne zużycie: {total_consumption:.2f} kWh")
        print(f"Łączna produkcja: {total_production:.2f} kWh")
        print(f"Handlowana energia (OZE): {total_traded_energy:.2f} kWh, średnia cena: {avg_trade_price:.2f} PLN/kWh")
        print(f"Tokeny mintowane w tym kroku: {token_rewards_this_step:.2f}")
        if grid_purchase > 0:
            print(f"Niedobór energii: {grid_purchase:.2f} kWh, zakupione z gridu po {grid_price:.2f} PLN/kWh (koszt: {grid_cost:.2f} PLN)")
            print(f"Tokeny spalane z powodu gridu: {burned_tokens:.2f}")
        else:
            print("Brak zakupu energii z gridu.")
        if self.storage:
            print(f"Stan magazynu po interwencji: {self.storage.current_level:.2f} kWh")
        print("Salda tokenów:")
        for agent_id, balance in self.token_balances.items():
            print(f"  {agent_id}: {balance:.2f} CT")
        print(f"Fundusz spółdzielni: {self.community_token_balance:.2f} CT")
        self.print_leaderboard()
        print("=" * 50)

        self.history_consumption.append(total_consumption)
        self.history_production.append(total_production)
        self.history_traded_energy.append(total_traded_energy)
        self.history_grid_purchase.append(grid_purchase)
        self.history_storage.append(self.storage.current_level if self.storage else None)
        self.history_avg_trade_price.append(avg_trade_price)
        self.history_token_reward.append(token_rewards_this_step)
        self.history_grid_penalty.append(burned_tokens)
        self.history_token_balance.append(self.community_token_balance)
        self.history_p2p_price.append(p2p_base_price)
        self.history_grid_price.append(grid_price)

    def simulate(self, steps, p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, hourly_data):
        for step in range(steps):
            self.simulate_step_with_negotiation(step, p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, hourly_data)