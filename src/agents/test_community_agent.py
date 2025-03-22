import os
import sys
from datetime import datetime
from pathlib import Path

# Add the root directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

import dotenv

from src.agents.community_agent import CommunityAgent

dotenv.load_dotenv()


def test_community_agent():
    """Test the community agent with sample data."""

    # Check if API key is available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY environment variable not set.")
        print("Please set it before running this test.")
        return

    # Create agent
    agent = CommunityAgent()

    # Sample test data
    current_hour = datetime(2023, 6, 15, 12, 0)  # June 15, 2023, 12:00

    grid_prices = {
        "purchase": 0.25,  # Price to buy from grid
        "sale": 0.15,  # Price to sell to grid
    }

    # Sample PPE predictions
    ppe_predictions = [
        {"ppe_id": "PPE_1", "production": 5.0, "consumption": 1.0},
        {"ppe_id": "PPE_2", "production": 3.0, "consumption": 2.0},
        {"ppe_id": "PPE_3", "production": 2.0, "consumption": 4.0},
    ]

    # Sample storage levels
    storage_levels = {
        "storage_1": {"current_level": 8.0, "capacity": 10.0},
        "storage_2": {"current_level": 3.0, "capacity": 15.0},
    }

    print(f"Testing community agent decision at {current_hour}")
    decision = agent.decide_grid_action(
        current_hour, grid_prices, ppe_predictions, storage_levels
    )

    print("\nCommunity agent decision:")
    print(f"Action: {decision.get('action')}")
    print(f"Amount: {decision.get('amount')} kWh")
    print(f"Explanation: {decision.get('explanation')}")

    # If there was an error
    if "error" in decision:
        print(f"Error: {decision['error']}")


if __name__ == "__main__":
    test_community_agent()
