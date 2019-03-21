FROM python
RUN  apt-get update
RUN mkdir /subscriber
WORKDIR /subscriber
COPY requirements.txt ./
COPY . /subscriber
RUN pip install --no-cache-dir -r requirements.txt
CMD python3 /subscriber/mqtt_subscriber.py