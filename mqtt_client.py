# !/usr/bin/env python3
import time
import os
import sys, traceback
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt
import logging


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


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    MQTTClient.connection_successful = True


class MQTTClient:
    continue_poll = False
    connection_successful = False

    def __init__(self):
        self.mqtt_broker = None
        self.mqtt_broker_instance = None
        self.mqtt_broker_port = None
        self.message = None
        self.enqueue_topic = None
        self.messages_per_second = 0
        self.test_duration_in_sec = 0
        self.log_level = None

        # create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # create console handler and set level to debug
        self.ch = logging.StreamHandler()
        self.ch.setLevel(logging.INFO)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        self.ch.setFormatter(formatter)

        # add ch to logger
        self.logger.addHandler(self.ch)

        self.load_environment_variables()
        self.mqtt_client_instance = None

        self.mqtt_client_instance = mqtt.Client()
        self.mqtt_client_instance.on_connect = on_connect

        self.connect()

    def load_environment_variables(self):
        while not self.mqtt_broker and \
                not self.mqtt_broker_port and \
                not self.message and \
                not self.enqueue_topic and \
                not self.messages_per_second and \
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
            self.log_level = os.getenv("log_level_key", default="info")

        self.logger.info(("mqtt_broker={},\n"
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

    def connect(self):
        self.mqtt_client_instance.connect(self.mqtt_broker, self.mqtt_broker_port, 60)

    def perform_job(self):
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

        self.exec_every_n_seconds(self.enqueue_mqtt_message)

    def exec_every_n_seconds(self, function_to_be_executed):
        first_called = datetime.now()
        previous_time = datetime.now()
        while MQTTClient.continue_poll:
            function_to_be_executed()
            current_time = datetime.now()

            execution_time = current_time - previous_time
            total_execution_time = current_time - first_called

            self.logger.info("current execution_time_micro sec={},"
                             "current execution time in sec={},"
                             "total_execution_time_sec={}"
                             .format(execution_time.microseconds,
                                     execution_time.seconds,
                                     total_execution_time.seconds))

            if total_execution_time.seconds > self.test_duration_in_sec:
                MQTTClient.continue_poll = False
            else:
                if execution_time.seconds > 1:
                    self.logger.info("Not sleeping now.")
                else:
                    sleep_time = 1 - execution_time.microseconds*(10**(-6))
                    if sleep_time > 0:
                        self.logger.info("Sleeping for {} milliseconds.".format(sleep_time))
                        time.sleep(1 - execution_time.microseconds * (10 ** (-6)))
            previous_time = current_time


    def enqueue_mqtt_message(self):
        for index in range(self.messages_per_second):
            """
            self.logger.debug("enqueuing MQTT message {} to topic at {}:{}."
                          .format(self.message,
                                  self.enqueue_topic,
                                  self.mqtt_broker,
                                  self.mqtt_broker_port))
            """
            self.mqtt_client_instance.publish(self.enqueue_topic,
                                          self.message)

    def cleanup(self):
        pass


if __name__ == '__main__':
    worker = MQTTClient()
    MQTTClient.continue_poll = True
    try:
        worker.perform_job()
    except KeyboardInterrupt:
        print("Keyboard interrupt." + sys.exc_info()[0])
        print("Exception in user code:")
        print("-" * 60)
        traceback.print_exc(file=sys.stdout)
        print("-" * 60)
        MQTTClient.continue_poll = False
