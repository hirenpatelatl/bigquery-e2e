FROM google/cloud-sdk
RUN apt-get update && apt-get install -y git vim python-pip
RUN pip install --upgrade google-api-python-client
RUN git config --global user.email "hirenpatelatl@gmail.com"
RUN git config --global user.name "hirenpatelatl"
WORKDIR /home
RUN git clone https://github.com/hirenpatelatl/bigquery-e2e.git
WORKDIR /home/bigquery-e2e/samples
EXPOSE 8080

