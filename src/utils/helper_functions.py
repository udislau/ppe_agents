def log_message(message):
    print(f"[LOG] {message}")

def save_results_to_file(results, filename):
    with open(filename, 'w') as file:
        for result in results:
            file.write(f"{result}\n")

def visualize_data(data):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 5))
    plt.plot(data['time_steps'], data['values'])
    plt.xlabel('Time Steps')
    plt.ylabel('Values')
    plt.title('Simulation Results')
    plt.grid()
    plt.show()