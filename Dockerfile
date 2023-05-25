
# Use the Python 3 base image
FROM python:3.9

# ENV PIP_DISABLE_PIP_VERSION_CHECK=1
# ENV PYTHONUNBUFFERED=1
# ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

COPY setup.py .
RUN python3.9 setup.py install


# Copy neccessary file to run client on tensorflow lenet model
# COPY training_process/client ./training_process/client
# COPY training_process/client/data_preprocessing.py ./client/data_preprocessing.py
# COPY training_process/client/Lenet.py ./client/Lenet.py
# COPY training_process/client/run_client.py ./client/run_client.py
#
# COPY mnist dataset
# COPY training_process/client/data ./data
#
# # Set the entrypoint to run the Python script
# ENTRYPOINT ["python", "client/run_client.py"]
