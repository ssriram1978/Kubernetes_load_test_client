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


class Transformer:
    """
    This Class is used to transform a message from one topic into another message to another topic in a message queue.
    """

    consumer_instance = None
    producer_instance = None

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.test_duration_in_sec = 0
        self.incoming_topic = None
        self.outgoing_topic = None
        self.log_level = None
        self.redis_server_hostname = None
        self.redis_server_port = None
        self.load_environment_variables()
        self.redis_instance = RedisInterface("Transformer")

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
        logging.info("test_duration_in_sec={},\n"
                     "log_level={},\n"
                     .format(self.test_duration_in_sec,
                             self.log_level))

    @staticmethod
    def on_message(msg):
        """
        The callback for when a PUBLISH message is received from the server.
        :param userdata:
        :param msg:
        :return:
        """
        logging.debug("Received message {}.".format(msg))
        Transformer.producer_instance.publish(msg)

    def perform_job(self):
        """
        Perform subscription.
        :return:
        """
        Transformer.producer_instance = PublisherSubscriberAPI(is_producer=True,
                                                               thread_identifier='Producer')

        Transformer.consumer_instance = PublisherSubscriberAPI(is_consumer=True,
                                                               thread_identifier='Consumer',
                                                               subscription_cb=Transformer.on_message)
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
        Transformer.producer_instance.cleanup()
        Transformer.consumer_instance.cleanup()


if __name__ == '__main__':
    worker = Transformer()
    Transformer.continue_poll = True
    try:
        worker.perform_job()
    except KeyboardInterrupt:
        logging.error("Keyboard interrupt." + sys.exc_info()[0])
        logging.error("Exception in user code:")
        logging.error("-" * 60)
        traceback.print_exc(file=sys.stdout)
        logging.error("-" * 60)
        Transformer.continue_poll = False
