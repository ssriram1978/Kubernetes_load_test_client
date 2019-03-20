FROM python
RUN  apt-get update
RUN mkdir /publisher
WORKDIR /publisher
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
CMD python3 /publisher/mqtt_publisher.py