import json
import os
from typing import Literal

import anthropic
from claudetools.tools.tool import Tool
from pydantic import BaseModel


class DecideGridAction(BaseModel):
    action: Literal["BUY", "SELL", "NONE"]
    amount: float
    explanation: str


functions = [
    {
        "name": "decide_grid_action",
        "description": "Decide whether to buy from or sell to the grid",
        "parameters": DecideGridAction.model_json_schema(),
    }
]


class CommunityAgent:
    """
    Community-level agent responsible for energy trading decisions.
    Uses LLM to decide whether to buy from or sell to the grid based on
    current community state, storage levels, and grid prices.
    """

    def __init__(self, api_key=None):
        """
        Initialize the community agent.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env variable)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = Tool(
            self.api_key,
        )

    def _format_prompt(
        self, current_hour, grid_prices, ppe_predictions, storage_levels
    ):
        """
        Format a prompt for the LLM with current community state information.

        Args:
            current_hour: Current datetime
            grid_prices: Dictionary with 'purchase' and 'sale' prices
            ppe_predictions: List of dictionaries with PPE predictions
            storage_levels: Dictionary with storage information

        Returns:
            Formatted prompt string
        """
        # Format PPE predictions
        ppe_str = ""
        total_production = 0
        total_consumption = 0

        for i, pred in enumerate(ppe_predictions):
            ppe_id = pred.get("ppe_id", f"PPE_{i+1}")
            production = pred.get("production", 0)
            consumption = pred.get("consumption", 0)

            total_production += production
            total_consumption += consumption

            ppe_str += f"{ppe_id}: production={production:.2f}, consumption={consumption:.2f}, net={production-consumption:.2f}\n"

        net_community = total_production - total_consumption

        # Format storage information
        storage_str = ""
        total_capacity = 0
        total_current = 0

        for storage_id, info in storage_levels.items():
            current = info.get("current_level", 0)
            capacity = info.get("capacity", 0)

            total_capacity += capacity
            total_current += current

            storage_str += f"{storage_id}: current={current:.2f}, capacity={capacity:.2f}, percentage={100*current/capacity if capacity > 0 else 0:.1f}%\n"

        prompt = f"""You are an AI agent managing an energy community's interactions with the power grid.
Your task is to decide whether to buy electricity from the grid or sell to the grid based on the current situation.

Current hour: {current_hour}

Grid prices:
- Purchase price (buying from grid): {grid_prices['purchase']}
- Sale price (selling to grid): {grid_prices['sale']}

Community energy status:
- Total predicted production: {total_production:.2f} kWh
- Total predicted consumption: {total_consumption:.2f} kWh
- Net community production: {net_community:.2f} kWh (positive means excess, negative means deficit)

Individual PPE predictions:
{ppe_str}

Storage status:
- Total current storage: {total_current:.2f} kWh
- Total storage capacity: {total_capacity:.2f} kWh
- Storage utilization: {100*total_current/total_capacity if total_capacity > 0 else 0:.1f}%

Individual storage levels:
{storage_str}

Based on this information, decide the optimal action:
1. If the community has excess energy (positive net) and storage is nearly full, consider selling to the grid
2. If the community has deficit energy (negative net) and storage is low, consider buying from the grid
3. If prices are favorable for selling and storage has sufficient capacity, consider selling to maximize profit
4. If prices are favorable for buying and storage has sufficient capacity, consider buying to store energy

Return your decision in the following JSON format:
{{
  "action": "[BUY, SELL, or NONE]",
  "amount": [amount of energy to buy or sell in kWh],
  "explanation": "[brief explanation of your reasoning]"
}}
"""
        return prompt

    def decide_grid_action(
        self, current_hour, grid_prices, ppe_predictions, storage_levels
    ):
        """
        Decide whether to buy from or sell to the grid.

        Args:
            current_hour: Current datetime
            grid_prices: Dictionary with 'purchase' and 'sale' prices
            ppe_predictions: List of dictionaries with PPE predictions
            storage_levels: Dictionary with storage information

        Returns:
            Dictionary with action decision
        """
        prompt = self._format_prompt(
            current_hour, grid_prices, ppe_predictions, storage_levels
        )

        # Call Anthropic API
        message = self.client(
            model="claude-3-7-sonnet-20250219",
            max_tokens=500,
            temperature=0.1,
            attach_system=None,
            tools=functions,
            messages=[{"role": "user", "content": prompt}],
        )

        response = message["parameters"]

        return response
