#!/bin/bash

# Activate conda environment
source activate asynfed


# Run the python file
nohup python client_234_gpu1.py --address 128.214.254.126:8080 > 234_gpu1.log 2>&1 &