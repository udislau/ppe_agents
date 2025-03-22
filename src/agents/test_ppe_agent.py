import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Add the root directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agents.ppe_agent import PPEAgent

load_dotenv()


def test_ppe_agent():
    """Test the PPE agent with a sample data file."""

    # Check if API key is available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY environment variable not set.")
        print("Please set it before running this test.")
        return

    # Path to sample data file
    # Adjust this path to point to your actual data file
    data_path = "pv_profiles/pv_profile_2023_06_PPE_1_prosument.csv"

    # Create agent
    agent = PPEAgent(ppe_id="PPE_1", historical_data_path=data_path)

    # Test prediction for a specific time
    test_time = datetime(2023, 6, 15, 12, 0)  # June 15, 2023, 12:00

    print(f"Predicting energy for PPE_1 at {test_time}")
    prediction = agent.predict_next_hour(test_time)

    print(f"\nPrediction for next hour (13:00):")
    print(f"Production: {prediction.get('production')} kWh")
    print(f"Consumption: {prediction.get('consumption')} kWh")
    print(f"Explanation: {prediction.get('explanation')}")

    # If there was an error
    if "error" in prediction:
        print(f"Error: {prediction['error']}")


if __name__ == "__main__":
    test_ppe_agent()
