import os
import re
from datetime import datetime, timedelta

import pandas as pd
from claudetools.tools.tool import Tool
from pydantic import BaseModel


class PredictNextHour(BaseModel):
    production: float
    consumption: float
    explanation: str


functions = [
    {
        "name": "predict_next_hour",
        "description": "Predict energy production and consumption for the next hour",
        "parameters": PredictNextHour.model_json_schema(),
    }
]


class PPEAgent:
    """
    Agent representing a single Point of Power Exchange (PPE) in the energy community.
    Uses LLM to predict energy consumption and production for the next hour.
    """

    def __init__(self, ppe_id, historical_data_path, api_key=None):
        """
        Initialize the PPE agent with its ID and historical data.

        Args:
            ppe_id: Unique identifier for this PPE
            historical_data_path: Path to CSV file containing historical energy data
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env variable)
        """
        self.ppe_id = ppe_id
        self.historical_data = self._load_historical_data(historical_data_path)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = Tool(
            self.api_key,
        )

    def _load_historical_data(self, file_path):
        """Load and process historical data from CSV file."""
        df = pd.read_csv(file_path)

        # Fix for timestamps with 24:00 as the hour
        # Convert '2023-06-07 24:00' to '2023-06-08 00:00'
        def fix_timestamp(timestamp):
            # Use regex to match timestamps with 24:00
            match = re.match(r"(\d{4}-\d{2}-\d{2}) 24:00", str(timestamp))
            if match:
                # Parse the date part
                date = datetime.strptime(match.group(1), "%Y-%m-%d")
                # Add one day and set hour to 00:00
                next_day = date + timedelta(days=1)
                return next_day.strftime("%Y-%m-%d 00:00")
            return timestamp

        # Apply the fix to the hour column
        df["hour"] = df["hour"].apply(fix_timestamp)

        # Convert hour column to datetime
        df["hour"] = pd.to_datetime(df["hour"])
        return df

    def _format_prompt(self, current_hour, window_size=72):
        """
        Format a prompt for the LLM including relevant historical data.

        Args:
            current_hour: Current datetime
            window_size: How many recent hours of data to include

        Returns:
            Formatted prompt string
        """
        # Convert current_hour to datetime if it's a string
        if isinstance(current_hour, str):
            current_hour = pd.to_datetime(current_hour)

        # Filter historical data to get recent entries
        recent_data = self.historical_data[self.historical_data["hour"] < current_hour]
        recent_data = recent_data.tail(window_size)

        # Format data for prompt
        data_entries = []
        for _, row in recent_data.iterrows():
            entry = f"hour: {row['hour']}, production: {row['production']}, consumption: {row['consumption']}"
            data_entries.append(entry)

        data_str = "\n".join(data_entries)

        prompt = f"""You are an AI agent for Point of Power Exchange (PPE) with ID {self.ppe_id}.
Your task is to predict energy production and consumption for the next hour based on historical patterns.

Current hour: {current_hour}

Recent historical data:
{data_str}

Based on this data, predict the energy production and consumption for the next hour.
Consider time of day, patterns in the data, and any trends you observe.

Return your prediction in the following JSON format:
{{
  "production": [predicted production value],
  "consumption": [predicted consumption value],
  "explanation": "[brief explanation of your reasoning]"
}}
"""
        return prompt

    def predict_next_hour(self, current_hour):
        """
        Predict energy production and consumption for the next hour.

        Args:
            current_hour: Current datetime

        Returns:
            Dictionary with production and consumption predictions
        """
        prompt = self._format_prompt(current_hour)

        # Call Anthropic API
        message = self.client(
            model="claude-3-7-sonnet-20250219",
            max_tokens=300,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
            attach_system=None,
            tools=functions,
        )

        return message["parameters"]

    def update_with_actual(self, hour, actual_production, actual_consumption):
        """
        Update agent with actual values after they become available.
        This could be used for learning/adaptation in more advanced implementations.

        Args:
            hour: Hour of the actual data
            actual_production: Actual energy production value
            actual_consumption: Actual energy consumption value
        """
        # In a more advanced implementation, this could update internal models
        # or provide feedback to improve future predictions
        pass
