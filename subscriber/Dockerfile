FROM python:3.6
RUN  apt-get update
RUN mkdir /parent_directory
RUN mkdir /parent_directory/subscriber
WORKDIR /parent_directory/subscriber
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /parent_directory/subscriber
ADD  infrastructure_components.tar.gz /parent_directory
CMD python3 /parent_directory/subscriber/subscriber.py
