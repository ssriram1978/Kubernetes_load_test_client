FROM docker.elastic.co/logstash/logstash:7.0.0
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
RUN rm -f /usr/share/logstash/config/pipelines.yml
# Add your logstash plugins setup here
RUN logstash-plugin install logstash-filter-json
RUN logstash-plugin install logstash-filter-grok
RUN logstash-plugin install logstash-input-beats
ADD pipeline/ /usr/share/logstash/pipeline/
ADD config/ /usr/share/logstash/config/
