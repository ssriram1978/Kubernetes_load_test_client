FROM python:3.6
RUN  apt-get update
RUN apt-get install -y default-jre
RUN apt-get install -y default-jdk
RUN mkdir /parent_directory
RUN mkdir /parent_directory/transformer
WORKDIR /parent_directory/transformer
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /parent_directory/transformer
ADD  infrastructure_components.tar.gz /parent_directory
CMD python3 /parent_directory/transformer/transformer.py
