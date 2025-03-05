import random
import os
import pandas as pd
import matplotlib.pyplot as plt
from src.models.cooperative import Cooperative

def load_profiles(directory):
    profiles = {}
    for filename in os.listdir(directory):
        if filename.endswith(".csv"):
            filepath = os.path.join(directory, filename)
            df = pd.read_csv(filepath)
            ppe = filename.split('_')[-1].split('.')[0]  # Wyciągnij nazwę PPE z nazwy pliku
            profiles[ppe] = df
    return profiles

def save_results_to_csv(cooperative, time_labels, ppe_labels):
    data = {
        'Time': time_labels,
        'PPE': ppe_labels,
        'Total Consumption': cooperative.history_consumption,
        'Total Production': cooperative.history_production,
        'Token Balance': cooperative.history_token_balance,
        'P2P Price': cooperative.history_p2p_price,
        'Grid Price': cooperative.history_grid_price,
        'Storage Level': cooperative.history_storage
    }
    df = pd.DataFrame(data)
    df.to_csv('simulation_results.csv', index=False)

# --- Przykładowa konfiguracja i uruchomienie symulacji ---

if __name__ == "__main__":
    config = {
        'storage': {'id': 'S1', 'capacity': 120}
    }
    
    cooperative = Cooperative(config, initial_token_balance=100)
    
    # Załaduj dane z katalogu pv_profiles
    profiles_directory = "pv_profiles"
    profiles = load_profiles(profiles_directory)
    
    # Ustal liczbę iteracji na podstawie liczby godzin w plikach
    steps = len(next(iter(profiles.values())))
    
    # Przygotuj dane godzinowe na podstawie załadowanych profili
    hourly_data = []
    time_labels = []
    ppe_labels = []
    for hour in range(steps):
        hour_data = {'hour': hour, 'consumption': 0, 'production': 0}
        for ppe, profile in profiles.items():
            hour_data['consumption'] += profile.iloc[hour]['consumption']
            hour_data['production'] += profile.iloc[hour]['production']
            if len(time_labels) < steps:
                time_labels.append(profile.iloc[hour]['hour'])
                ppe_labels.append(ppe)
        hourly_data.append(hour_data)
    
    p2p_base_price = 0.5
    grid_price = 1.0
    min_price = 0.2
    token_mint_rate = 0.1
    token_burn_rate = 0.1
    
    cooperative.simulate(steps, p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, hourly_data)
    
    # Zapisz dane wynikowe do plików CSV
    save_results_to_csv(cooperative, time_labels, ppe_labels)
    
    # Generowanie etykiet dla osi X
    labels = time_labels
    
    # Modyfikacja metody plot_results, aby używała nowych etykiet i zapisywała wykres do pliku
    def plot_results(self, steps, labels):
        fig, ax = plt.subplots(4, 1, figsize=(15, 15))
        
        ax[0].plot(range(steps), self.history_consumption, label='Total Consumption')
        ax[0].plot(range(steps), self.history_production, label='Total Production')
        ax[0].set_title('Energy Consumption and Production')
        ax[0].set_xlabel('Time')
        ax[0].set_ylabel('Energy (kWh)')
        ax[0].legend()
        ax[0].set_xticks(range(steps))
        ax[0].set_xticklabels(labels, rotation=90)
        
        ax[1].plot(range(steps), self.history_token_balance, label='Token Balance')
        ax[1].set_title('Token Balance Over Time')
        ax[1].set_xlabel('Time')
        ax[1].set_ylabel('Tokens')
        ax[1].legend()
        ax[1].set_xticks(range(steps))
        ax[1].set_xticklabels(labels, rotation=90)
        
        ax[2].plot(range(steps), self.history_p2p_price, label='P2P Price')
        ax[2].plot(range(steps), self.history_grid_price, label='Grid Price')
        ax[2].set_title('Energy Prices Over Time')
        ax[2].set_xlabel('Time')
        ax[2].set_ylabel('Price (Tokens/kWh)')
        ax[2].legend()
        ax[2].set_xticks(range(steps))
        ax[2].set_xticklabels(labels, rotation=90)
        
        ax[3].plot(range(steps), self.history_storage, label='Storage Level')
        ax[3].set_title('Storage Level Over Time')
        ax[3].set_xlabel('Time')
        ax[3].set_ylabel('Energy (kWh)')
        ax[3].legend()
        ax[3].set_xticks(range(steps))
        ax[3].set_xticklabels(labels, rotation=90)
        
        plt.tight_layout()
        plt.savefig('results.png')  # Zapisz wykres do pliku
        plt.show()
    
    # Przypisanie zmodyfikowanej metody do obiektu cooperative
    cooperative.plot_results = plot_results.__get__(cooperative)
    
    cooperative.plot_results(steps, labels)