FROM python:3.6
RUN  apt-get update
RUN mkdir /parent_directory
RUN mkdir /parent_directory/orchestrator
WORKDIR /parent_directory/orchestrator
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /parent_directory/orchestrator
ADD  infrastructure_components.tar.gz /parent_directory
CMD python3 /parent_directory/orchestrator/orchestrator.py
