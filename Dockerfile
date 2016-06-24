FROM google/cloud-sdk
RUN apt-get update && apt-get install -y git vim python-pip wget curl
RUN pip install --upgrade google-api-python-client
WORKDIR /home
COPY . /home/bigquery-e2e
WORKDIR /home/bigquery-e2e/samples

