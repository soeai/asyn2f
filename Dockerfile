
# Use the Python 3 base image
FROM python:3.9

WORKDIR /app

COPY . .

# install dependencies for the program
RUN pip install -r requirements.txt
# install asynfed package as pip package 
RUN python3.9 setup.py install
