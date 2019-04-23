# !/usr/bin/env python3
import logging
import os
import sys
import time
import traceback
from datetime import datetime

logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',
                    level=logging.INFO,
                    datefmt='%m/%d/%Y %I:%M:%S %p')

import json
from io import StringIO


def import_all_paths():
    realpath = os.path.realpath(__file__)
    # print("os.path.realpath({})={}".format(__file__,realpath))
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


class Publisher:
    """
    This class publishes JSON messages to a broker.
    """

    def __init__(self):
        """
        Initialize variables.
        """
        self.message = None
        self.messages_per_second = 0
        self.test_duration_in_sec = 0
        self.log_level = None
        self.json_parsed_data = None
        self.publisher_key_name = None
        self.container_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.container_id = self.container_id[:12]
        self.redis_instance = RedisInterface()
        self.producer_consumer_instance = PublisherSubscriberAPI(is_producer=True,
                                                                 thread_identifier='Producer')
        self.broker_type = None
        self.load_environment_variables()
        self.set_log_level()
        self.publish_container_id_to_redis()
        self.parse_message_into_json()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.message or \
                not self.messages_per_second or \
                not self.test_duration_in_sec or \
                not self.publisher_key_name:
            time.sleep(1)
            self.message = os.getenv("message_key",
                                     default=None)
            self.messages_per_second = int(os.getenv("messages_per_second_key",
                                                     default='0'))
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.publisher_key_name = os.getenv("publisher_key_name",
                                                default=None)
            self.log_level = os.getenv("log_level_key",
                                       default="info")

        logging.info(("message={},\n"
                      "messages_per_second={},\n"
                      "test_duration_in_sec={},\n"
                      "publisher_key_name={},\n"
                      "self.log_level={}.\n"
                      .format(self.message,
                              self.messages_per_second,
                              self.test_duration_in_sec,
                              self.publisher_key_name,
                              self.log_level)))

    def set_log_level(self):
        """
        Create Logger.
        :return:
        """
        pass

    def publish_container_id_to_redis(self):
        if self.redis_instance:
            self.redis_instance.append_value_to_a_key(self.publisher_key_name,
                                                      self.container_id + ' ')

    def parse_message_into_json(self):
        """
        Convert message to JSON object.
        :return:
        """
        self.json_parsed_data = json.loads(self.message)
        logging.debug("JSON parsed message = {}".format(self.json_parsed_data))
        logging.debug("timestamp = {}".format(self.json_parsed_data['lastUpdated']))

    def perform_job(self):
        self.exec_every_one_second(self.enqueue_message)
        raise KeyboardInterrupt

    def exec_every_one_second(self, function_to_be_executed):
        """
        Execute the passed in function every one second.
        Note 1: If the passed in function takes more than one second, then execute the function immediately.
        Note 2: If the passed in function takes less than a second, then compute the delta time and sleep.
        :param function_to_be_executed:
        :return:
        """
        first_called = datetime.now()
        previous_time = datetime.now()
        current_total_time = 0
        while current_total_time < self.test_duration_in_sec:
            function_to_be_executed()
            current_time = datetime.now()

            execution_time = current_time - previous_time
            total_execution_time = current_time - first_called
            current_total_time = total_execution_time.seconds
            logging.info("current execution_time_micro sec={},"
                         "current execution time in sec={},"
                         "current_total_time={}"
                         .format(execution_time.microseconds,
                                 execution_time.seconds,
                                 current_total_time))
            if execution_time.seconds > 1:
                logging.info("Not sleeping now.")
            else:
                sleep_time = 1 - execution_time.microseconds * (10 ** (-6))
                if sleep_time > 0:
                    logging.info("Sleeping for {} milliseconds.".format(sleep_time))
                    time.sleep(1 - execution_time.microseconds * (10 ** (-6)))
            previous_time = current_time

    def enqueue_message(self):
        """
        Enqueue message to a broker.
        :return:
        """
        for index in range(self.messages_per_second):
            self.json_parsed_data['lastUpdated'] = datetime.now().isoformat()
            io = StringIO()
            json.dump(self.json_parsed_data, io)
            logging.debug("enqueuing message {}."
                          .format(io.getvalue()))
            self.producer_consumer_instance.publish(io.getvalue())

    def cleanup(self):
        pass


if __name__ == '__main__':
    worker = Publisher()
    try:
        worker.perform_job()
    except KeyboardInterrupt:
        logging.error("Keyboard interrupt." + sys.exc_info()[0])
        logging.error("Exception in user code:")
        logging.error("-" * 60)
        traceback.print_exc(file=sys.stdout)
        logging.error("-" * 60)
