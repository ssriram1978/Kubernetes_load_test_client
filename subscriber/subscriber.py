# !/usr/bin/env python3
import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from collections import deque

import dateutil.parser

logging.basicConfig(format='%(message)s',
                    level=logging.INFO)


def import_all_paths():
    realpath = os.path.realpath(__file__)
    # print("os.path.realpath({})={}".format(__file__,realpath)`)
    dirname = os.path.dirname(realpath)
    # print("os.path.dirname({})={}".format(realpath,dirname))
    dirname_list = dirname.split('/')
    # print(dirname_list)
    for index in range(len(dirname_list)):
        module_path = '/'.join(dirname_list[:index])
        # print("module_path={}".format(module_path))
        try:
            sys.path.append(module_path)
        except:
            # print("Invalid module path {}".format(module_path))
            pass


import_all_paths()

from infrastructure_components.redis_client.redis_interface import RedisInterface
from infrastructure_components.publisher_subscriber.publisher_subscriber import PublisherSubscriberAPI


class Subscriber:
    """
    This Class is used to subscribe to a topic in a message queue.
    """
    message_queue = deque()
    redis_instance = None
    latency_compute_start_key_name = None

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.average_latency_for_n_sec = 0
        self.test_duration_in_sec = 0
        self.log_level = None
        self.container_id = os.popen("cat /etc/hostname").read()
        self.container_id = self.container_id[:-1]
        self.latency_publish_name = None
        self.max_consumer_threads = 1
        self.producer_consumer_instance = None
        self.subscriber_key_name = None
        self.is_loopback = False
        self.redis_server_hostname = None
        self.redis_server_port = None
        self.load_environment_variables()
        self.create_logger()
        Subscriber.redis_instance = RedisInterface("Subscriber")
        self.publish_container_id_to_redis()
        self.create_latency_compute_thread()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not Subscriber.latency_compute_start_key_name:
            time.sleep(1)
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.log_level = os.getenv("log_level_key",
                                       default="info")
            self.subscriber_key_name = os.getenv("subscriber_key_name",
                                                 default=None)
            self.latency_publish_name = os.getenv("latency_publish_key",
                                                  default="latency")
            Subscriber.latency_compute_start_key_name = os.getenv("latency_compute_start_key_name_key",
                                                                  default=None)
            self.max_consumer_threads = int(os.getenv("max_consumer_threads_key",
                                                      default='1'))
            if os.getenv("is_loopback_key", default="false") == "true":
                self.is_loopback = True

        logging.info(("test_duration_in_sec={},\n"
                      "log_level={},\n"
                      "is_loopback={},\n"
                      "latency_publish_name={},\n"
                      "container_id={},\n"
                      "latency_compute_start_key_name={},\n"
                      "subscriber_key_name={},\n"
                      "max_consumer_threads={}."
                      .format(self.test_duration_in_sec,
                              self.log_level,
                              self.is_loopback,
                              self.latency_publish_name,
                              self.container_id,
                              Subscriber.latency_compute_start_key_name,
                              self.subscriber_key_name,
                              self.max_consumer_threads)))

    def create_logger(self):
        """
        Create Logger.
        :return:
        """
        pass

    def publish_container_id_to_redis(self):
        published_successfully = False
        while not published_successfully:
            if Subscriber.redis_instance:
                logging.info("Trying to Publish key = {}, value = {} in redis."
                             .format(self.subscriber_key_name,
                                     self.container_id + ' '))
                self.redis_instance.append_value_to_a_key(self.subscriber_key_name,
                                                          self.container_id + ' ')
                value = self.redis_instance.get_value_based_upon_the_key(self.subscriber_key_name)
                if not value or value.decode('utf-8').find(self.container_id) == -1:
                    logging.info(
                        "Unable to publish key = {}, value = {} in redis. Trying to reconnect and sleep for 1 second."
                        .format(self.subscriber_key_name,
                                self.container_id + ' '))
                    self.redis_instance.reconnect()
                    time.sleep(1)
                else:
                    published_successfully = True

    @staticmethod
    def on_message(msg):
        """
        The callback for when a PUBLISH message is received from the server.
        :param userdata:
        :param msg:
        :return:
        """
        logging.debug("Received message {}.".format(msg))
        msgq_message = (datetime.now().isoformat(timespec='microseconds'),
                        msg)
        Subscriber.message_queue.append(msgq_message)

    def create_latency_compute_thread(self):
        self.latency_compute_thread = [0] * self.max_consumer_threads
        for index in range(self.max_consumer_threads):
            self.latency_compute_thread[index] = threading.Thread(name="{}{}"
                                                                  .format("latency_compute_thread",
                                                                          index),
                                                                  target=Subscriber.run_latency_compute_thread,
                                                                  args=(),
                                                                  kwargs={'container_id': self.container_id,
                                                                          'latency_name': self.latency_publish_name}
                                                                  )
            self.latency_compute_thread[index].do_run = True
            self.latency_compute_thread[index].name = "{}_{}".format("latency_compute_thread", index)
            self.latency_compute_thread[index].start()

    @staticmethod
    def run_latency_compute_thread(*args, **kwargs):
        logging.info("Starting {}".format(threading.current_thread().getName()))
        container_id = None
        latency_name = None
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'container_id':
                container_id = value
            elif name == 'latency_name':
                latency_name = value
        t = threading.currentThread()
        is_first_key_published_in_redis = False
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                dequeued_message = Subscriber.message_queue.popleft()
                msg_rcvd_timestamp, msg = dequeued_message[0], dequeued_message[1]
                if not is_first_key_published_in_redis:
                    if Subscriber.latency_compute_start_key_name:
                        json_parsed_data = json.loads(msg)
                        Subscriber.redis_instance.append_value_to_a_key(latency_name,
                                                                        latency_name + '_' + container_id + ' ')
                        Subscriber.redis_instance.set_key_to_value_within_name(
                            latency_name + '_' + container_id,
                            Subscriber.latency_compute_start_key_name,
                            json_parsed_data['lastUpdated'])
                        is_first_key_published_in_redis = True
                Subscriber.parse_message_and_compute_latency(msg,
                                                             msg_rcvd_timestamp,
                                                             latency_name + '_' + container_id)
            except:
                logging.debug("No more messages.")
                time.sleep(0.1)
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))

    @staticmethod
    def publish_latency_in_redis_db(time_difference, topic, timestamp_from_message):
        try:
            dt = None
            latency = time_difference.microseconds / 1000
            logging.info("Sent_timestamp:{},Latency_in_milliseconds:{}".format(timestamp_from_message,
                                                                               latency))
            if Subscriber.redis_instance:
                ts = dateutil.parser.parse(timestamp_from_message)
                dt = ts.isoformat(timespec='seconds')
                value = Subscriber.redis_instance.get_list_of_values_based_upon_a_key(topic, str(dt))[0]
                if not value:
                    value = [latency]
                else:
                    value = eval(value.decode('utf8'))
                    value.append(latency)
                Subscriber.redis_instance.set_key_to_value_within_name(topic, str(dt), str(value))
        except:
            logging.error("{}: Unable to connect to redis.".format(threading.current_thread().getName()))

    @staticmethod
    def parse_message_and_compute_latency(message, msg_rcvd_timestamp, topic):
        json_parsed_data = json.loads(message)
        time_difference = dateutil.parser.parse(msg_rcvd_timestamp) - dateutil.parser.parse(
            json_parsed_data['lastUpdated'])
        Subscriber.publish_latency_in_redis_db(time_difference, topic, json_parsed_data['lastUpdated'])

    def perform_job(self):
        """
        Perform subscription.
        :return:
        """
        self.producer_consumer_instance = PublisherSubscriberAPI(is_consumer=True,
                                                                 thread_identifier='Consumer',
                                                                 subscription_cb=Subscriber.on_message)
        while True:
            try:
                time.sleep(60)
            except:
                self.cleanup()

    def cleanup(self):
        self.producer_consumer_instance.cleanup()
        for index in range(self.max_consumer_threads):
            self.latency_compute_thread[index].do_run = False
        time.sleep(5)
        for index in range(self.max_consumer_threads):
            logging.debug("Trying to join thread {}."
                          .format(self.latency_compute_thread[index].getName()))
            self.latency_compute_thread[index].join(1.0)
            time.sleep(1)


if __name__ == '__main__':
    worker = Subscriber()
    Subscriber.continue_poll = True
    try:
        worker.perform_job()
    except KeyboardInterrupt:
        logging.error("Keyboard interrupt." + sys.exc_info()[0])
        logging.error("Exception in user code:")
        logging.error("-" * 60)
        traceback.print_exc(file=sys.stdout)
        logging.error("-" * 60)
        Subscriber.continue_poll = False
