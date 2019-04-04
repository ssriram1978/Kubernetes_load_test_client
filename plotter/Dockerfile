FROM python
RUN  apt-get update
RUN mkdir /parent_directory
RUN mkdir /parent_directory/plotter
WORKDIR /parent_directory/plotter
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /parent_directory/plotter
ADD  infrastructure_components.tar.gz /parent_directory
CMD python3 /parent_directory/plotter/plotter.py