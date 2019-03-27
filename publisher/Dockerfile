FROM python
RUN  apt-get update
RUN mkdir /parent_directory
RUN mkdir /parent_directory/publisher
WORKDIR /parent_directory/publisher
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /parent_directory/publisher
ADD  infrastructure_components.tar.gz /parent_directory
CMD python3 /parent_directory/publisher/publisher.py