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

from publisher_subscriber.publisher_subscriber import PublisherSubscriberAPI
from redis_client.redis_interface import RedisInterface

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


class Subscriber:
    """
    This Class is used to subscribe to a topic in a message queue.
    """
    message_queue = []

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.average_latency_for_n_sec = 0
        self.test_duration_in_sec = 0
        self.log_level = None
        self.max_consumer_threads = 1
        self.redis_instance = RedisInterface()
        self.producer_consumer_instance = None
        self.is_loopback = False
        self.load_environment_variables()
        self.create_logger()
        self.create_latency_compute_thread()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.test_duration_in_sec:
            time.sleep(1)
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.log_level = os.getenv("log_level_key",
                                       default="info")
            self.max_consumer_threads = int(os.getenv("max_consumer_threads_key",
                                                      default='1'))
            if os.getenv("is_loopback_key", default="false") == "true":
                self.is_loopback = True

        logging.info(("test_duration_in_sec={},\n"
                      "log_level={},\n"
                      "is_loopback={},\n"
                      "max_consumer_threads={}."
                      .format(self.test_duration_in_sec,
                              self.log_level,
                              self.is_loopback,
                              self.max_consumer_threads)))

    def create_logger(self):
        """
        Create Logger.
        :return:
        """
        pass

    def on_message(self, client, userdata, msg):
        """
        The callback for when a PUBLISH message is received from the server.
        :param userdata:
        :param msg:
        :return:
        """
        msgq_message = (datetime.now().isoformat(timespec='microseconds'),
                        msg.payload)
        Subscriber.message_queue.append(msgq_message)
        self.redis_instance.increment_dequeue_count()
        self.redis_instance.write_an_event_in_redis_db("Consumer {}: Dequeued Message = {}"
                                                   .format(self.thread_identifier,
                                                           msg))

    def create_latency_compute_thread(self):
        self.latency_compute_thread = [0] * self.max_consumer_threads
        for index in range(self.max_consumer_threads):
            self.latency_compute_thread[index] = threading.Thread(name="{}{}".format("latency_compute_thread", index),
                                                                  target=Subscriber.run_latency_compute_thread)
            self.latency_compute_thread[index].do_run = True
            self.latency_compute_thread[index].name = "{}_{}".format("latency_compute_thread", index)
            self.latency_compute_thread[index].start()

    @staticmethod
    def run_latency_compute_thread():
        logging.info("Starting {}".format(threading.current_thread().getName()))
        t = threading.currentThread()
        current_index = 0
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                dequeued_message = Subscriber.message_queue[current_index]
                msg_rcvd_timestamp, msg = dequeued_message[0], dequeued_message[1]
                Subscriber.parse_message_and_compute_latency(msg, msg_rcvd_timestamp)
                current_index += 1
            except:
                logging.info("No more messages.")
                del Subscriber.message_queue
                Subscriber.message_queue = []
                time.sleep(0.1)
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))

    @staticmethod
    def parse_message_and_compute_latency(message, msg_rcvd_timestamp):
        json_parsed_data = json.loads(message)
        time_difference = dateutil.parser.parse(msg_rcvd_timestamp) - dateutil.parser.parse(
            json_parsed_data['lastUpdated'])
        if time_difference.seconds:
            logging.info("{}:Latency in seconds = {}.{}".format(threading.current_thread().getName(),
                                                                time_difference.seconds,
                                                                time_difference.microseconds))
        elif time_difference.microseconds:
            logging.info("{}:Latency in milliseconds = {}".format(threading.current_thread().getName(),
                                                                  time_difference.microseconds / 10 ** 3))

    def perform_job(self):
        """
        Perform subscription.
        :return:
        """
        self.producer_consumer_instance = PublisherSubscriberAPI(is_consumer=True,
                                                                 subscription_cb=self.on_message)
    def cleanup(self):
        pass


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
