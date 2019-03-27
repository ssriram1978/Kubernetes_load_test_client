# !/usr/bin/env python3
import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime

import dateutil.parser

logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',
                    level=logging.INFO,
                    datefmt='%m/%d/%Y %I:%M:%S %p')


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

from infrastructure_components.publisher_subscriber.publisher_subscriber import PublisherSubscriberAPI
from infrastructure_components.redis_client.redis_interface import RedisInterface


class Subscriber:
    """
    This Class is used to subscribe to a topic in a message queue.
    """
    message_queue = []
    max_queue_size = 10000
    redis_instance = None

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.average_latency_for_n_sec = 0
        self.test_duration_in_sec = 0
        self.log_level = None
        self.topic = None
        self.latency_publish_name = None
        self.max_consumer_threads = 1
        self.producer_consumer_instance = None
        self.is_loopback = False
        self.redis_server_hostname = None
        self.redis_server_port = None
        self.load_environment_variables()
        self.create_logger()
        Subscriber.redis_instance = RedisInterface("Subscriber")
        self.create_latency_compute_thread()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.test_duration_in_sec or \
                not self.topic:
            time.sleep(1)
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.log_level = os.getenv("log_level_key",
                                       default="info")
            self.latency_publish_name = os.getenv("latency_publish_key",
                                                  default="latency")
            self.max_consumer_threads = int(os.getenv("max_consumer_threads_key",
                                                      default='1'))
            if os.getenv("is_loopback_key", default="false") == "true":
                self.is_loopback = True

            self.topic = os.getenv("topic_key", default=None)

        logging.info(("test_duration_in_sec={},\n"
                      "log_level={},\n"
                      "is_loopback={},\n"
                      "latency_publish_name={},\n"
                      "topic={},\n"
                      "max_consumer_threads={}."
                      .format(self.test_duration_in_sec,
                              self.log_level,
                              self.is_loopback,
                              self.latency_publish_name,
                              self.topic,
                              self.max_consumer_threads)))

    def create_logger(self):
        """
        Create Logger.
        :return:
        """
        pass

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
                                                                  kwargs={'topic': self.topic,
                                                                          'latency_name': self.latency_publish_name}
                                                                  )
            self.latency_compute_thread[index].do_run = True
            self.latency_compute_thread[index].name = "{}_{}".format("latency_compute_thread", index)
            self.latency_compute_thread[index].start()

    @staticmethod
    def run_latency_compute_thread(*args, **kwargs):
        logging.info("Starting {}".format(threading.current_thread().getName()))
        topic = None
        latency_name = None
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'topic':
                topic = value
            elif name == 'latency_name':
                latency_name = value
        t = threading.currentThread()
        current_index = 0
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                dequeued_message = Subscriber.message_queue[current_index]
                msg_rcvd_timestamp, msg = dequeued_message[0], dequeued_message[1]
                Subscriber.parse_message_and_compute_latency(msg, msg_rcvd_timestamp, topic + '_' + latency_name)
                current_index += 1
                if current_index >= Subscriber.max_queue_size:
                    del Subscriber.message_queue
                    Subscriber.message_queue = []
                    current_index = 0
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
            logging.info("{}:Latency in milliseconds = {}".format(threading.current_thread().getName(),
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
        start_time = time.time()
        time.sleep(1)
        end_time = time.time()
        while end_time - start_time < self.test_duration_in_sec:
            logging.debug("total test duration = {},current_test_duration = {}."
                          .format(self.test_duration_in_sec, (end_time - start_time)))
            time.sleep(1)
            end_time = time.time()
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
