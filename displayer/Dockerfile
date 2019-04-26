FROM python
RUN  apt-get update
RUN mkdir /parent_directory
RUN mkdir /parent_directory/displayer
WORKDIR /parent_directory/displayer
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /parent_directory/displayer
ADD  infrastructure_components.tar.gz /parent_directory
CMD python3 /parent_directory/displayer/displayer.py