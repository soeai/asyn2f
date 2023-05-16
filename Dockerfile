
# Use the Python 3 base image
FROM python:3

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

COPY setup.py .
COPY .env .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the 'asynfed' folder
COPY asynfed ./asynfed

RUN pip install --upgrade pip
RUN python setup.py install

# Copy the 'client' folder
COPY test/main_test/client ./client

RUN cd ./client

# Set the entrypoint to run the Python script
ENTRYPOINT ["python", "./client/test_client.py"]
