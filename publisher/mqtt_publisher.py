# !/usr/bin/env python3
import time
import os
import sys, traceback
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt
import logging
import json
from io import StringIO

def import_all_packages():
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


import_all_packages()


class MQTTClientPublisher:
    """
    This class publishes MQTT messages to a MQTT broker.
    """
    def __init__(self):
        """
        Initialize variables.
        """
        self.mqtt_broker = None
        self.mqtt_broker_instance = None
        self.mqtt_broker_port = None
        self.message = None
        self.enqueue_topic = None
        self.messages_per_second = 0
        self.test_duration_in_sec = 0
        self.log_level = None
        self.mqtt_client_instance = None
        self.json_parsed_data = None
        self.load_environment_variables()
        self.create_logger()
        self.parse_message_into_json()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.mqtt_broker or \
                not self.mqtt_broker_port or \
                not self.message or \
                not self.enqueue_topic or \
                not self.messages_per_second or \
                not self.test_duration_in_sec:
            time.sleep(1)
            self.mqtt_broker = os.getenv("mqtt_broker_key",
                                         default=None)
            self.mqtt_broker_port = int(os.getenv("mqtt_broker_port_key",
                                                  default=0))
            self.message = os.getenv("message_key",
                                     default=None)
            self.enqueue_topic = os.getenv("enqueue_topic_key",
                                           default=None)
            self.messages_per_second = int(os.getenv("messages_per_second_key",
                                                     default='0'))
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.log_level = os.getenv("log_level_key",
                                       default="info")

        logging.error(("mqtt_broker={},\n"
                          "mqtt_broker_port={},\n"
                          "message={},\n"
                          "enqueue_topic={},\n"
                          "messages_per_second={},\n"
                          "test_duration_in_sec={},\n"
                          "self.log_level={}.\n"
                          .format(self.mqtt_broker,
                                  self.mqtt_broker_port,
                                  self.message,
                                  self.enqueue_topic,
                                  self.messages_per_second,
                                  self.test_duration_in_sec,
                                  self.log_level)))

    def create_logger(self):
        """
        Create Logger.
        :return:
        """
        # create logger
        self.logger = logging.getLogger(__name__)

        # create console handler and set level to debug
        self.ch = logging.StreamHandler()

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        self.ch.setFormatter(formatter)

        # add ch to logger
        self.logger.addHandler(self.ch)

        if self.log_level.find('info'):
            self.logger.setLevel(logging.INFO)
            self.ch.setLevel(logging.INFO)
        elif self.log_level.find('debug'):
            self.logger.setLevel(logging.DEBUG)
            self.ch.setLevel(logging.DEBUG)
        elif self.log_level.find('warn'):
            self.logger.setLevel(logging.WARNING)
            self.ch.setLevel(logging.WARNING)
        elif self.log_level.find('error'):
            self.logger.setLevel(logging.ERROR)
            self.ch.setLevel(logging.ERROR)

    def connect(self):
        """
        Connect to a MQTT broker.
        :return:
        """

        self.mqtt_client_instance = mqtt.Client()
        self.mqtt_client_instance.on_connect = self.on_connect
        self.mqtt_client_instance.connect(self.mqtt_broker, self.mqtt_broker_port, 60)

    def on_connect(self, client, userdata, flags, rc):
        """
        The callback for when the client receives a CONNACK response from the server.
        :param client:
        :param userdata:
        :param flags:
        :param rc:
        :return:
        """
        logging.error("Connected with result code " + str(rc))
        self.exec_every_one_second(self.enqueue_mqtt_message)

    def parse_message_into_json(self):
        """
        Convert message to JSON object.
        :return:
        """
        self.json_parsed_data = json.loads(self.message)
        self.logger.info("JSON parsed message = {}".format(self.json_parsed_data))
        self.logger.info("timestamp = {}".format(self.json_parsed_data['lastUpdated']))

    def perform_job(self):
        """
        Publish MQTT messages every n seconds.
        :return:
        """
        self.connect()
        self.exec_every_one_second(self.enqueue_mqtt_message)
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
            self.logger.info("current execution_time_micro sec={},"
                             "current execution time in sec={},"
                             "current_total_time={}"
                             .format(execution_time.microseconds,
                                     execution_time.seconds,
                                     current_total_time))
            if execution_time.seconds > 1:
                self.logger.info("Not sleeping now.")
            else:
                sleep_time = 1 - execution_time.microseconds * (10 ** (-6))
                if sleep_time > 0:
                    self.logger.info("Sleeping for {} milliseconds.".format(sleep_time))
                    time.sleep(1 - execution_time.microseconds * (10 ** (-6)))
            previous_time = current_time

    def enqueue_mqtt_message(self):
        """
        Enqueue MQTT message to a MQTT broker.
        :return:
        """
        for index in range(self.messages_per_second):
            self.json_parsed_data['lastUpdated'] = datetime.now().isoformat(timespec='microseconds')
            io = StringIO()
            json.dump(self.json_parsed_data, io)

            self.logger.debug("enqueuing MQTT message {} to topic at {}:{}."
                          .format(io.getvalue(),
                                  self.enqueue_topic,
                                  self.mqtt_broker,
                                  self.mqtt_broker_port))

            self.mqtt_client_instance.publish(self.enqueue_topic,
                                              io.getvalue())

    def cleanup(self):
        pass


if __name__ == '__main__':
    worker = MQTTClientPublisher()
    try:
        worker.perform_job()
    except KeyboardInterrupt:
        print("Keyboard interrupt." + sys.exc_info()[0])
        print("Exception in user code:")
        print("-" * 60)
        traceback.print_exc(file=sys.stdout)
        print("-" * 60)

