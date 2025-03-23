#!/bin/bash

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY environment variable is not set."
    echo "Please set it using: export ANTHROPIC_API_KEY='your-api-key'"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required dependencies
echo "Checking and installing dependencies..."
pip install pandas anthropic matplotlib claudetools python-dotenv

# Set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Default paths
STORAGE_PATH="config/storages.json"
PROFILES_DIR="pv_profiles_2_days"
LOG_DIR="logs"
GRID_COSTS_PATH="config/grid_costs.csv"

# Create directories if they don't exist
mkdir -p results
mkdir -p $LOG_DIR

# Run the simulation
echo "Running simulation..."
python3 src/simulation/agent_based_simulation.py $STORAGE_PATH $PROFILES_DIR $LOG_DIR $GRID_COSTS_PATH

# Check if simulation was successful
if [ $? -eq 0 ]; then
    echo "Simulation completed successfully!"
    echo "Results saved in the 'results' directory."
else
    echo "Simulation failed. Please check the logs for details."
fi 