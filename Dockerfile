
# Use the Python 3 base image
FROM python:3

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

COPY setup.py .
# COPY .env .

# Install dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

# Copy the 'asynfed' folder
COPY asynfed ./asynfed

# RUN pip install --upgrade pip
RUN python setup.py install

# Copy neccessary file to run client on tensorflow lenet model
# COPY training_process/client ./training_process/client
COPY training_process/client/data_preprocessing.py ./client/data_preprocessing.py
COPY training_process/client/Lenet.py ./client/Lenet.py
COPY training_process/client/run_client.py ./client/run_client.py

# COPY mnist dataset
COPY training_process/client/data ./data

# Set the entrypoint to run the Python script
ENTRYPOINT ["python", "client/run_client.py"]
