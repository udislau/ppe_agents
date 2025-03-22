import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add the root directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from src.agents.community_agent import CommunityAgent
from src.agents.ppe_agent import PPEAgent
from src.models.cooperative import Cooperative
from src.utils.helper_functions import (
    load_profiles,
    load_storages,
    plot_results,
    save_results_to_csv,
)

load_dotenv()


def load_grid_costs(filepath):
    """Load grid costs from a CSV file."""
    grid_costs = []
    with open(filepath, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            grid_costs.append(
                {
                    "hour": row["Hour"],
                    "purchase": float(row["Purchase"].replace(",", ".")),
                    "sale": float(row["Sale"].replace(",", ".")),
                }
            )
    return grid_costs


def run_agent_simulation(
    storage_path, profiles_dir, log_dir, grid_costs_path, steps=None
):
    """
    Run the agent-based simulation.

    Args:
        storage_path: Path to storage configuration file
        profiles_dir: Path to directory containing profile CSV files
        log_dir: Path to directory to save logs
        grid_costs_path: Path to grid costs file
        steps: Number of simulation steps (defaults to length of profiles)
    """
    # Load storage configuration
    storages = load_storages(storage_path)

    # Initialize the cooperative
    config = {"storages": storages}
    cooperative = Cooperative(config, initial_token_balance=100)

    # Load profiles
    profiles = load_profiles(profiles_dir)

    # Create PPE agents (one per profile)
    ppe_agents = {}
    for ppe_id, profile_data in profiles.items():
        # Find the corresponding profile file
        profile_file = None
        for file in Path(profiles_dir).glob("*.csv"):
            if ppe_id in file.name:
                profile_file = str(file)
                break

        if profile_file:
            ppe_agents[ppe_id] = PPEAgent(
                ppe_id=ppe_id, historical_data_path=profile_file
            )
        else:
            print(f"Warning: Could not find profile file for {ppe_id}")

    # Create community agent
    community_agent = CommunityAgent()

    # Load grid costs
    grid_costs = load_grid_costs(grid_costs_path)

    # Determine number of steps
    if steps is None:
        steps = len(next(iter(profiles.values())))

    # Prepare time labels
    time_labels = []

    # Prepare to record results
    simulation_results = {
        "hour": [],
        "total_production": [],
        "total_consumption": [],
        "net_energy": [],
        "grid_purchase": [],
        "grid_sale": [],
        "storage_level": [],
    }

    # Extract the first profile to get time information
    sample_profile = next(iter(profiles.values()))

    # Simulation loop
    print(f"Starting simulation with {len(ppe_agents)} PPE agents...")

    for step in range(steps):
        # Get current hour from the profile data
        current_hour = sample_profile.iloc[step]["hour"]
        time_labels.append(current_hour)

        print(f"\nSimulation step {step+1}/{steps}: {current_hour}")

        # Get grid prices for this hour
        grid_price = {
            "purchase": grid_costs[step % len(grid_costs)]["purchase"],
            "sale": grid_costs[step % len(grid_costs)]["sale"],
        }

        # Get PPE predictions for this hour
        ppe_predictions = []
        total_production = 0
        total_consumption = 0

        for ppe_id, agent in ppe_agents.items():
            # Get actual data (in a real predictive scenario, we'd use predictions)
            actual_data = profiles[ppe_id].iloc[step]

            # In a fully agent-based simulation, we'd use this:
            # prediction = agent.predict_next_hour(current_hour)

            # For testing, we'll use actual data but in a real system we'd use predictions
            prediction = {
                "ppe_id": ppe_id,
                "production": actual_data["production"],
                "consumption": actual_data["consumption"],
                "explanation": "Using actual data for testing",
            }

            total_production += prediction["production"]
            total_consumption += prediction["consumption"]
            ppe_predictions.append(prediction)

            print(
                f"  {ppe_id}: Production={prediction['production']:.2f}, Consumption={prediction['consumption']:.2f}"
            )

        # Get current storage levels
        storage_levels = {}
        total_storage = 0
        for storage in cooperative.storages:
            storage_levels[storage.name] = {
                "current_level": storage.current_charge,
                "capacity": storage.capacity,
            }
            total_storage += storage.current_charge

        # Get community agent decision
        decision = community_agent.decide_grid_action(
            current_hour, grid_price, ppe_predictions, storage_levels
        )

        print(
            f"  Community decision: {decision['action']} {decision['amount']:.2f} kWh"
        )
        print(f"  Explanation: {decision['explanation']}")

        # Process the decision to update energy flows
        net_energy = total_production - total_consumption
        grid_purchase = 0
        grid_sale = 0

        if decision["action"] == "BUY":
            grid_purchase = decision["amount"]
            # Add energy to storage
            for storage in cooperative.storages:
                # Calculate how much we can add to this storage
                available_capacity = storage.capacity - storage.current_charge
                to_store = min(available_capacity, grid_purchase)

                if to_store > 0:
                    storage.current_charge += to_store
                    grid_purchase -= to_store

                    if grid_purchase <= 0:
                        break

        elif decision["action"] == "SELL":
            # Check if we have enough energy in storage
            available_from_storage = total_storage

            if available_from_storage >= decision["amount"]:
                grid_sale = decision["amount"]

                # Take energy from storage
                remaining_to_take = grid_sale
                for storage in cooperative.storages:
                    to_take = min(storage.current_charge, remaining_to_take)
                    storage.current_charge -= to_take
                    remaining_to_take -= to_take

                    if remaining_to_take <= 0:
                        break
            else:
                grid_sale = available_from_storage

                # Take all available energy from storage
                for storage in cooperative.storages:
                    storage.current_charge = 0

        # Handle prosumer energy
        if net_energy > 0:
            # We have excess energy to store
            for storage in cooperative.storages:
                available_capacity = storage.capacity - storage.current_charge
                to_store = min(available_capacity, net_energy)

                if to_store > 0:
                    storage.current_charge += to_store
                    net_energy -= to_store

                    if net_energy <= 0:
                        break

            # If we still have excess energy, sell it to the grid
            if net_energy > 0:
                grid_sale += net_energy
        else:
            # We need energy - take from storage first
            energy_needed = -net_energy

            for storage in cooperative.storages:
                to_take = min(storage.current_charge, energy_needed)

                if to_take > 0:
                    storage.current_charge -= to_take
                    energy_needed -= to_take

                    if energy_needed <= 0:
                        break

            # If we still need energy, buy from the grid
            if energy_needed > 0:
                grid_purchase += energy_needed

        # Update total storage level
        total_storage = sum(storage.current_charge for storage in cooperative.storages)

        # Record results
        simulation_results["hour"].append(current_hour)
        simulation_results["total_production"].append(total_production)
        simulation_results["total_consumption"].append(total_consumption)
        simulation_results["net_energy"].append(total_production - total_consumption)
        simulation_results["grid_purchase"].append(grid_purchase)
        simulation_results["grid_sale"].append(grid_sale)
        simulation_results["storage_level"].append(total_storage)

        print(
            f"  Grid Purchase: {grid_purchase:.2f} kWh, Grid Sale: {grid_sale:.2f} kWh"
        )
        print(f"  Total Storage Level: {total_storage:.2f} kWh")

    # Create results directory
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    now = datetime.now()
    formatted_date = now.strftime("%Y-%m-%d_%H-%M-%S")

    # Save simulation results to CSV
    results_df = pd.DataFrame(simulation_results)
    results_df.to_csv(
        results_dir / f"agent_simulation_{formatted_date}.csv", index=False
    )

    # Save detailed results
    with open(results_dir / f"agent_details_{formatted_date}.json", "w") as f:
        json.dump(
            {
                "steps": steps,
                "ppe_count": len(ppe_agents),
                "storage_count": len(cooperative.storages),
                "results": {
                    k: (
                        [
                            float(v) if isinstance(v, (int, float)) else str(v)
                            for v in vals
                        ]
                        if isinstance(vals, list)
                        else vals
                    )
                    for k, vals in simulation_results.items()
                },
            },
            f,
            indent=2,
            default=str,
        )

    # Plot results
    plot_agent_results(simulation_results, time_labels, results_dir, formatted_date)

    print(f"\nSimulation completed. Results saved to {results_dir}")
    return simulation_results, time_labels


def plot_agent_results(results, time_labels, results_dir, timestamp):
    """
    Plot the simulation results.

    Args:
        results: Dictionary with simulation results
        time_labels: List of time labels
        results_dir: Directory to save plots
        timestamp: Timestamp string for file naming
    """
    try:
        import matplotlib.pyplot as plt

        # Energy production/consumption plot
        plt.figure(figsize=(15, 8))
        plt.plot(
            range(len(time_labels)),
            results["total_production"],
            "g-",
            label="Total Production",
        )
        plt.plot(
            range(len(time_labels)),
            results["total_consumption"],
            "r-",
            label="Total Consumption",
        )
        plt.plot(
            range(len(time_labels)), results["net_energy"], "b--", label="Net Energy"
        )
        plt.title("Energy Production and Consumption")
        plt.xlabel("Hour")
        plt.ylabel("Energy (kWh)")
        plt.legend()
        plt.xticks(
            range(0, len(time_labels), 24),
            [time_labels[i].split(" ")[0] for i in range(0, len(time_labels), 24)],
            rotation=45,
        )
        plt.tight_layout()
        plt.savefig(results_dir / f"energy_balance_{timestamp}.png")

        # Grid interaction plot
        plt.figure(figsize=(15, 8))
        plt.plot(
            range(len(time_labels)),
            results["grid_purchase"],
            "r-",
            label="Grid Purchase",
        )
        plt.plot(range(len(time_labels)), results["grid_sale"], "g-", label="Grid Sale")
        plt.title("Grid Interactions")
        plt.xlabel("Hour")
        plt.ylabel("Energy (kWh)")
        plt.legend()
        plt.xticks(
            range(0, len(time_labels), 24),
            [time_labels[i].split(" ")[0] for i in range(0, len(time_labels), 24)],
            rotation=45,
        )
        plt.tight_layout()
        plt.savefig(results_dir / f"grid_interactions_{timestamp}.png")

        # Storage level plot
        plt.figure(figsize=(15, 8))
        plt.plot(
            range(len(time_labels)),
            results["storage_level"],
            "b-",
            label="Storage Level",
        )
        plt.title("Energy Storage Level")
        plt.xlabel("Hour")
        plt.ylabel("Energy (kWh)")
        plt.legend()
        plt.xticks(
            range(0, len(time_labels), 24),
            [time_labels[i].split(" ")[0] for i in range(0, len(time_labels), 24)],
            rotation=45,
        )
        plt.tight_layout()
        plt.savefig(results_dir / f"storage_level_{timestamp}.png")

    except ImportError:
        print("Warning: matplotlib not installed. Skipping plot generation.")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "Usage: python agent_based_simulation.py <storage_path> <profiles_dir> <log_dir> <grid_costs_path> [steps]"
        )
        sys.exit(1)

    storage_path = sys.argv[1]
    profiles_dir = sys.argv[2]
    log_dir = sys.argv[3]
    grid_costs_path = sys.argv[4]

    steps = None
    if len(sys.argv) > 5:
        steps = int(sys.argv[5])

    run_agent_simulation(storage_path, profiles_dir, log_dir, grid_costs_path, steps)
