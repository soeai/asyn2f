#!/bin/bash

# Activate conda environment
source activate tensorlfow-cpu


# Run the python file
nohup python client_local.py --address 128.214.254.126:8080 > client_local.log 2>&1 &