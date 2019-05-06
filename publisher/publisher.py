# !/usr/bin/env python3
import logging
import os
import sys
import time
import traceback
from datetime import datetime
import threading, time

logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',
                    level=logging.INFO)

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
from infrastructure_components.redis_client.redis_interface import RedisInterface
from infrastructure_components.publisher_subscriber.publisher_subscriber import PublisherSubscriberAPI


class Publisher:
    """
    This class publishes JSON messages to a broker.
    """
    MILLI_SECONDS_TO_SPLIT_EVENLY_FOR_MESSAGES = 1000

    def __init__(self):
        """
        Initialize variables.
        """
        self.message = None
        self.messages_per_second = 0
        self.test_duration_in_sec = 0
        self.start_test_time = None
        self.current_time = None
        self.log_level = None
        self.json_parsed_data = None
        self.publisher_key_name = None
        self.container_id = os.popen("cat /etc/hostname").read()
        self.container_id = self.container_id[:-1]
        self.redis_instance = RedisInterface('Publisher')
        self.next_call = None
        self.broker_type = None
        self.load_environment_variables()
        self.timer_resolution = 0
        self.messages_per_millisecond = 0
        if self.messages_per_second > Publisher.MILLI_SECONDS_TO_SPLIT_EVENLY_FOR_MESSAGES:
            self.timer_resolution = 1 / Publisher.MILLI_SECONDS_TO_SPLIT_EVENLY_FOR_MESSAGES
            self.messages_per_millisecond = self.messages_per_second // \
                                            Publisher.MILLI_SECONDS_TO_SPLIT_EVENLY_FOR_MESSAGES
        else:
            self.timer_resolution = 1 / self.messages_per_second
            self.messages_per_millisecond = 1
        logging.info("timer_resolution={},messages_per_millisecond={}"
                     .format(self.timer_resolution, self.messages_per_millisecond))
        self.set_log_level()
        self.publish_container_id_to_redis()
        self.parse_message_into_json()
        self.producer_consumer_instance = PublisherSubscriberAPI(is_producer=True,
                                                                 thread_identifier='Producer')

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
        published_successfully = False
        while not published_successfully:
            if self.redis_instance:
                logging.info("Trying to Publish key = {}, value = {} in redis."
                             .format(self.publisher_key_name,
                                     self.container_id + ' '))
                self.redis_instance.append_value_to_a_key(self.publisher_key_name,
                                                          self.container_id + ' ')
                value = self.redis_instance.get_value_based_upon_the_key(self.publisher_key_name)
                if not value or value.decode('utf-8').find(self.container_id) == -1:
                    logging.info("Unable to publish key = {}, value = {} in redis. Sleeping for 1 second."
                                 .format(self.publisher_key_name,
                                         self.container_id + ' '))
                    time.sleep(1)
                else:
                    published_successfully = True

    def parse_message_into_json(self):
        """
        Convert message to JSON object.
        :return:
        """
        self.json_parsed_data = json.loads(self.message)
        logging.debug("JSON parsed message = {}".format(self.json_parsed_data))
        logging.debug("timestamp = {}".format(self.json_parsed_data['lastUpdated']))

    def perform_job(self):
        time.sleep(60)
        self.start_test_time = datetime.now()
        logging.info("Starting the load test at {}".format(self.start_test_time))
        self.exec_every_n_milliseconds()
        # self.exec_every_one_second(self.enqueue_message)
        while True:
            time.sleep(60)

    def enqueue_message(self):
        """
        Enqueue message to a broker.
        :return:
        """
        self.json_parsed_data['lastUpdated'] = datetime.now().isoformat()
        io = StringIO()
        json.dump(self.json_parsed_data, io)
        logging.debug("enqueuing message {}."
                      .format(io.getvalue()))
        self.producer_consumer_instance.publish(io.getvalue())

    def exec_every_n_milliseconds(self):
        for _ in range(self.messages_per_millisecond):
            self.enqueue_message()
        self.current_time = datetime.now()
        duration_in_sec = (self.current_time - self.start_test_time).seconds
        logging.debug("duration_in_sec={},total_test_duration={}."
                      .format(duration_in_sec,
                              self.test_duration_in_sec))
        if duration_in_sec < self.test_duration_in_sec:
            logging.debug("Invoking threading timer.")
            threading.Timer(interval=self.timer_resolution,
                            function=self.exec_every_n_milliseconds).start()
        else:
            logging.info("Stopping the producer because the test ran for {} seconds."
                         .format(duration_in_sec))

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
