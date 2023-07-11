#!/bin/bash

# Activate conda environment
source activate asynfed


# Run the python file
nohup python client_235_gpu.py --address 128.214.254.126:8080 > 235_gpu.log 2>&1 &