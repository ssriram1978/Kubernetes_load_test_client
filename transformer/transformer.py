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

from infrastructure_components.redis_client.redis_interface import RedisInterface
from infrastructure_components.publisher_subscriber.publisher_subscriber import PublisherSubscriberAPI


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
        self.container_id = os.popen("cat /etc/hostname").read()
        self.container_id = self.container_id[:-1]
        self.transformer_key_name = None
        self.load_environment_variables()
        self.redis_instance = RedisInterface("Transformer")
        self.publish_container_id_to_redis()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.transformer_key_name:
            time.sleep(1)
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.log_level = os.getenv("log_level_key",
                                       default="info")
            self.transformer_key_name = os.getenv("transformer_key_name",
                                                  default=None)
        logging.info("test_duration_in_sec={},\n"
                     "transformer_key_name={},\n"
                     "log_level={},\n"
                     .format(self.test_duration_in_sec,
                             self.transformer_key_name,
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
        while True:
            try:
                time.sleep(60)
            except:
                self.cleanup()

    def cleanup(self):
        Transformer.producer_instance.cleanup()
        Transformer.consumer_instance.cleanup()

    def publish_container_id_to_redis(self):
        published_successfully = False
        while not published_successfully:
            if self.redis_instance:
                logging.info("Trying to Publish key = {}, value = {} in redis."
                             .format(self.transformer_key_name,
                                     self.container_id + ' '))
                self.redis_instance.append_value_to_a_key(self.transformer_key_name,
                                                          self.container_id + ' ')
                value = self.redis_instance.get_value_based_upon_the_key(self.transformer_key_name)
                if not value or value.decode('utf-8').find(self.container_id) == -1:
                    logging.info(
                        "Unable to publish key = {}, value = {} in redis. Trying to reconnect and sleep for 1 second."
                        .format(self.transformer_key_name,
                                self.container_id + ' '))
                    self.redis_instance.reconnect()
                    time.sleep(1)
                else:
                    published_successfully = True


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
