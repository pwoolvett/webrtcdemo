# SAFE (powered by ODDL).

Version: v.0.0.0 - Codelco DVEN.

## Description

[Video Descriptivo]

SAFE is a Computer Vision system designed to analyze, monitor and enforce safety conditions on operational environments. 

Its workflow has been designed on top of three main blocks:

1. Object detection and tracking: SAFE leverages [PythIA]() to run computer vision deep learning models. These are used to detect and track objects in real time.
   
2. SafeZones: SafeZones are polygonal regions monitored by the system. Any detection that occurs within the region is further processed and saved in the corresponding database.
   
3. Data analysis: 
   
## Installation

### 1. Pre-requisites

  To ensure an appropiate operation, the following software is required:

  - [Docker](https://docs.docker.com/engine/install/)
  - [Docker-compose](https://docs.docker.com/compose/install/)
  - [Nvidia-container runtime](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#installing-on-ubuntu-and-debian)

### NOTE: SAFE has been tested only under Ubuntu 18.04

### 2. Clone this repo

  ```git
  git clone https://github.com/rmclabs-io/pilotoventanas.git
  ```

### 3. Build
  
  ```bash
  docker-compose build
  ```

### 4. Deploy

  ```bash
  docker-compose up
  ```

### 5. Access web-app

In a Firefox/Google Chrome browser, open the available webapp. By default, it's exposed on `https://localhost:9999`.

The deployment port can be changed under the `XXX` environment variable.

## Usage

### 1. View real-time streaming
[VIDEO EXPLICATIVO]

### 2. Check event registry
[VIDEO EXPLICATIVO]

### 3. View cumulative statistics
[VIDEO EXPLICATIVO]

## Roadmap

The project's roadmap is currently available in (link al kanban)

## Contribute

For a deeper explanation on each service, please visit the [wiki](./docs/wiki.md)

# REVISAR
Generate metrics from database query
generate histogram from database query
TODO: Maybe expose functionality via an API?
make backend/apt.list smaller