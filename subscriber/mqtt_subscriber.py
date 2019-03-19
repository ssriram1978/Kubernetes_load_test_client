# !/usr/bin/env python3
import time
import os
import sys, traceback
from datetime import datetime
import dateutil.parser
import threading
import paho.mqtt.client as mqtt
import logging
import json
from collections import deque


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


class MQTTClientSubscriber:
    """
    Class used to subscribe to a MQTT topic.
    """
    message_queue = deque()

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.mqtt_broker = None
        self.mqtt_broker_instance = None
        self.mqtt_broker_port = None
        self.dequeue_topic = None
        self.average_latency_for_n_sec = 0
        self.test_duration_in_sec = 0
        self.log_level = None
        self.mqtt_client_instance = None
        self.load_environment_variables()
        self.create_logger()
        self.create_latency_compute_thread()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.mqtt_broker or \
                not self.mqtt_broker_port or \
                not self.dequeue_topic or \
                not self.average_latency_for_n_sec or \
                not self.test_duration_in_sec:
            time.sleep(1)
            self.mqtt_broker = os.getenv("mqtt_broker_key",
                                         default=None)
            self.mqtt_broker_port = int(os.getenv("mqtt_broker_port_key",
                                                  default=0))
            self.dequeue_topic = os.getenv("enqueue_topic_key",
                                           default=None)
            self.average_latency_for_n_sec = int(os.getenv("average_latency_for_n_sec_key",
                                                     default='0'))
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.log_level = os.getenv("log_level_key",
                                       default="info")

        logging.error(("mqtt_broker={},\n"
                          "mqtt_broker_port={},\n"
                          "dequeue_topic={},\n"
                          "average_latency_for_n_sec={},\n"
                          "test_duration_in_sec={},\n"
                          "self.log_level={}.\n"
                          .format(self.mqtt_broker,
                                  self.mqtt_broker_port,
                                  self.dequeue_topic,
                                  self.average_latency_for_n_sec,
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
        Connect to the broker.
        :return:
        """
        self.mqtt_client_instance = mqtt.Client()
        self.mqtt_client_instance.on_connect = self.on_connect
        self.mqtt_client_instance.on_message = self.on_message
        self.mqtt_client_instance.connect(self.mqtt_broker, self.mqtt_broker_port, 60)
        self.mqtt_client_instance.loop_forever()

    def on_connect(self,client, userdata, flags, rc):
        """
        The callback for when the client receives a CONNACK response from the server.
        :param client:
        :param userdata:
        :param flags:
        :param rc:
        :return:
        """
        logging.error("Connected with result code " + str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe(self.dequeue_topic)

    def on_message(self,client, userdata, msg):
        """
        The callback for when a PUBLISH message is received from the server.
        :param userdata:
        :param msg:
        :return:
        """
        msgq_message = (datetime.now().isoformat(timespec='microseconds'),
                                                   msg.payload)
        MQTTClientSubscriber.message_queue.append(msgq_message)

    def create_latency_compute_thread(self):
        self.latency_compute_thread = threading.Thread(name="{}{}".format("latency_compute_thread", 1),
                                                        target=MQTTClientSubscriber.run_latency_compute_thread)
        self.latency_compute_thread.do_run = True
        self.latency_compute_thread.start()

    @staticmethod
    def run_latency_compute_thread():
        logging.error("Starting {}".format(threading.current_thread().getName()))
        t = threading.currentThread()
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                if len(MQTTClientSubscriber.message_queue):
                    dequeued_message = MQTTClientSubscriber.message_queue.popleft()
                    msg_rcvd_timestamp, msg = dequeued_message[0], dequeued_message[1]
                    MQTTClientSubscriber.parse_message_and_compute_latency(msg, msg_rcvd_timestamp)
            except:
                logging.error("caught an exception.")

    @staticmethod
    def parse_message_and_compute_latency(message, msg_rcvd_timestamp):
        json_parsed_data = json.loads(message)
        time_difference = dateutil.parser.parse(msg_rcvd_timestamp) - dateutil.parser.parse(json_parsed_data['lastUpdated'])
        if time_difference.seconds:
            logging.error("Latency in seconds = {}.{}".format(time_difference.seconds,
                                                      time_difference.microseconds))
        elif time_difference.microseconds:
            logging.error("Latency in milliseconds = {}".format(time_difference.microseconds / 10**3))

    def perform_job(self):
        """
        Perform subscription.
        :return:
        """
        self.connect()

    def cleanup(self):
        pass


if __name__ == '__main__':
    worker = MQTTClientSubscriber()
    MQTTClientSubscriber.continue_poll = True
    try:
        worker.perform_job()
    except KeyboardInterrupt:
        print("Keyboard interrupt." + sys.exc_info()[0])
        print("Exception in user code:")
        print("-" * 60)
        traceback.print_exc(file=sys.stdout)
        print("-" * 60)
        MQTTClientSubscriber.continue_poll = False
