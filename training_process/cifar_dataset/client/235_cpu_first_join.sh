#!/bin/bash

cd asynfed_5_chunks_2

# Remove directories if they exist
if [ -d "weights" ]; then
    rm -r "weights"
fi

if [ -d "logs" ]; then
    rm -r "logs"
fi

# Remove file if it exists
if [ -f "profile.json" ]; then
    rm "profile.json"
fi

# Activate conda environment
conda activate cpu

# Run the python file
python run_client.py --chunk_index 4
