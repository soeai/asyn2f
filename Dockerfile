FROM nvidia/cuda:11.4.3-cudnn8-devel-ubuntu20.04

RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y curl
RUN apt-get -y install python3
RUN apt-get -y install python3-pip


WORKDIR /app

COPY . .

# install dependencies for the program
RUN pip install -r requirements.txt
# install asynfed package as pip package 
