# filepath: /home/greg/prog/energy-agents/fetchai-agent-simulation/src/simulation/run_simulation.py
from src.agents.community_agent import CommunityAgent
from src.agents.member_agent import MemberAgent
from src.models.energy_source import EnergySource

import matplotlib.pyplot as plt

def run_simulation(num_time_steps):
    # Simulation setup
    community_agent = CommunityAgent("Community")
    community_agent.add_energy_source(EnergySource("Solar Farm", 100))
    community_agent.add_energy_source(EnergySource("Wind Turbine", 50))

    members = [MemberAgent("Alice"), MemberAgent("Bob"), MemberAgent("Charlie")]

    # Data collection lists
    time_steps = []
    energy_generated_data = []
    energy_consumed_data = {member.name: [] for member in members}
    ct_balance_data = {member.name: [] for member in members}

    # Simulation loop
    for time_step in range(num_time_steps):
        total_energy_generated = community_agent.generate_energy()
        print(f"Time Step {time_step}: Energy Generated = {total_energy_generated} kWh")

        for member in members:
            energy_consumed = member.consume_energy()
            community_agent.distribute_ct(member, energy_consumed)
            print(f"{member.name}: Energy Consumed = {energy_consumed} kWh, CT Balance = {member.ct_balance}")

        time_steps.append(time_step)
        energy_generated_data.append(total_energy_generated)

        for member in members:
            energy_consumed_data[member.name].append(energy_consumed)
            ct_balance_data[member.name].append(member.ct_balance)

    # Print final CT balances
    print("\nFinal CT Balances:")
    for member in members:
        print(f"{member.name}: {member.ct_balance}")

    # Plotting
    plt.figure(figsize=(12, 8))

    # Energy Generated
    plt.subplot(2, 1, 1)  # 2 rows, 1 column, first plot
    plt.plot(time_steps, energy_generated_data)
    plt.xlabel("Time Step")
    plt.ylabel("Energy Generated (kWh)")
    plt.title("Energy Generation Over Time")

    # Energy Consumption and CT Balance
    plt.subplot(2, 1, 2)  # 2 rows, 1 column, second plot
    for member in members:
        plt.plot(time_steps, energy_consumed_data[member.name], label=f"{member.name} Consumption")
        plt.plot(time_steps, ct_balance_data[member.name], label=f"{member.name} CT Balance", linestyle="--")

    plt.xlabel("Time Step")
    plt.ylabel("Energy/CT")
    plt.title("Energy Consumption and CT Balance Over Time")
    plt.legend()  # Show the legend for different lines

    plt.tight_layout()
    plt.savefig("energy_simulation.png")  # Save the image
    plt.close()  # Close the figure to prevent warnings

if __name__ == "__main__":
    run_simulation(num_time_steps=20)