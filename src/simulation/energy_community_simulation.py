from src.models.cooperative import Cooperative
from src.utils.helper_functions import plot_results, save_results_to_csv, load_profiles, load_storages
import sys


if __name__ == "__main__":

    if len(sys.argv) < 1:
        print("No required parameter: storage file path")
        sys.exit(1)
    if len(sys.argv) < 2:
        print("No required parameter: profiles directory path")
        sys.exit(1)
    
    
    storages = load_storages(sys.argv[1])
    
    config = {
        'storages': storages
    }
    
    cooperative = Cooperative(config, initial_token_balance=100)
    
    # Załaduj dane z katalogu pv_profiles
    profiles = load_profiles(sys.argv[2])
    
    # Ustal liczbę iteracji na podstawie liczby godzin w plikach
    steps = len(next(iter(profiles.values())))
    
    # Przygotuj dane godzinowe na podstawie załadowanych profili
    hourly_data = []
    time_labels = []
    for hour in range(steps):
        total_consumption = 0
        total_production = 0
        for ppe, profile in profiles.items():
            total_consumption += profile.iloc[hour]['consumption']
            total_production += profile.iloc[hour]['production']
        time_labels.append(profile.iloc[hour]['hour'])
        hourly_data.append({'hour': hour, 'consumption': total_consumption, 'production': total_production})
    
    p2p_base_price = 0.5
    grid_price = 1.0
    min_price = 0.2
    token_mint_rate = 0.1
    token_burn_rate = 0.1
    
    cooperative.simulate(len(hourly_data), p2p_base_price, grid_price, min_price, token_mint_rate, token_burn_rate, hourly_data)
    
    # Zapisz dane wynikowe do plików CSV
    save_results_to_csv(cooperative, time_labels)
    
    # Zapisz logi do pliku tekstowego
    cooperative.save_logs('simulation_logs.txt')
    
    # Generowanie etykiet dla osi X
    labels = time_labels

    # Przypisanie zmodyfikowanej metody do obiektu cooperative
    cooperative.plot_results = plot_results.__get__(cooperative)
    
    cooperative.plot_results(len(hourly_data), labels)