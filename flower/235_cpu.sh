#!/bin/bash

# Activate conda environment
source activate cpu


# Run the python file
nohup python client_235_cpu.py --address 128.214.254.126:8080 > 235_cpu.log 2>&1 &