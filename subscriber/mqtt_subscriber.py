# !/usr/bin/env python3
import time
import os
import sys, traceback
from datetime import datetime
import dateutil.parser
import threading
import paho.mqtt.client as mqtt
import logging
import redis

logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',
                    level=logging.INFO,
                    datefmt='%m/%d/%Y %I:%M:%S %p')

import json
from collections import deque


def import_all_packages():
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


import_all_packages()


class MQTTClientSubscriber:
    """
    Class used to subscribe to a MQTT topic.
    """
    message_queue = []

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
        self.max_consumer_threads = 1
        self.redis_instance = None
        self.redis_server_hostname = None
        self.redis_server_port = 0
        self.load_environment_variables()
        self.connect_to_redis_server()
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
                not self.redis_server_hostname or \
                not self.redis_server_port or \
                not self.test_duration_in_sec:
            time.sleep(1)
            self.mqtt_broker = os.getenv("mqtt_broker_key",
                                         default=None)
            self.mqtt_broker_port = int(os.getenv("mqtt_broker_port_key",
                                                  default=0))
            self.dequeue_topic = os.getenv("dequeue_topic_key",
                                           default=None)
            self.average_latency_for_n_sec = int(os.getenv("average_latency_for_n_sec_key",
                                                           default='0'))
            self.test_duration_in_sec = int(os.getenv("test_duration_in_sec_key",
                                                      default='0'))
            self.log_level = os.getenv("log_level_key",
                                       default="info")
            self.max_consumer_threads = int(os.getenv("max_consumer_threads_key",
                                                      default='1'))
            self.redis_server_hostname = os.getenv("redis_server_hostname_key",
                                                   default=None)
            self.redis_server_port = int(os.getenv("redis_server_port_key",
                                                   default=0))

        logging.info(("mqtt_broker={},\n"
                      "mqtt_broker_port={},\n"
                      "dequeue_topic={},\n"
                      "average_latency_for_n_sec={},\n"
                      "test_duration_in_sec={},\n"
                      "log_level={},\n"
                      "redis_server_hostname={},\n"
                      "redis_server_port={},\n"
                      "max_consumer_threads={}."
                      .format(self.mqtt_broker,
                              self.mqtt_broker_port,
                              self.dequeue_topic,
                              self.average_latency_for_n_sec,
                              self.test_duration_in_sec,
                              self.log_level,
                              self.redis_server_hostname,
                              self.redis_server_port,
                              self.max_consumer_threads)))

    def create_logger(self):
        """
        Create Logger.
        :return:
        """
        pass

    def connect_to_redis_server(self):
        while self.redis_instance is None:
            self.redis_instance = redis.StrictRedis(host=self.redis_server_hostname,
                                                    port=self.redis_server_port,
                                                    db=0)
            time.sleep(5)
        logging.info("Successfully connected "
                     "to redisClient server {},port {}"
                     .format(self.redis_server_hostname,
                             self.redis_server_port))

    def publish_topic_in_redis_db(self):
        cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        key = 'publisher' + '_' + cont_id[:12]
        value = self.enqueue_topic + '_' + cont_id[:12]
        return_value = False
        if self.redis_instance is not None:
            try:
                self.redis_instance.set(key, value)
                return_value = True
            except redis.exceptions.ConnectionError:
                logging.error("Unable to connect to Redis server.")
            except BaseException:
                logging.error("Base Except: Unable to connect to Redis server.")
        return return_value

    def connect(self):
        """
        Connect to the broker.
        :return:
        """
        self.mqtt_client_instance = mqtt.Client()
        self.mqtt_client_instance.on_connect = self.on_connect
        self.mqtt_client_instance.on_message = self.on_message
        is_connected = False
        while not is_connected:
            try:
                self.mqtt_client_instance.connect(self.mqtt_broker, self.mqtt_broker_port, 60)
                logging.info("Successfully connected to {}:{}".format(self.mqtt_broker, self.mqtt_broker_port))
                is_connected = True
            except:
                logging.error("Unable to connect to {}:{}".format(self.mqtt_broker, self.mqtt_broker_port))
                time.sleep(5)
        self.mqtt_client_instance.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        """
        The callback for when the client receives a CONNACK response from the server.
        :param client:
        :param userdata:
        :param flags:
        :param rc:
        :return:
        """
        logging.info("Connected with result code " + str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe(self.dequeue_topic)

    def on_message(self, client, userdata, msg):
        """
        The callback for when a PUBLISH message is received from the server.
        :param userdata:
        :param msg:
        :return:
        """
        start_time = datetime.now()
        msgq_message = (datetime.now().isoformat(timespec='microseconds'),
                        msg.payload)
        MQTTClientSubscriber.message_queue.append(msgq_message)
        time_elapsed = datetime.now() - start_time
        logging.debug('time elapsed to process this message. {} microseconds.'.format(time_elapsed.microseconds))

    def create_latency_compute_thread(self):
        self.latency_compute_thread = [0] * self.max_consumer_threads
        for index in range(self.max_consumer_threads):
            self.latency_compute_thread[index] = threading.Thread(name="{}{}".format("latency_compute_thread", index),
                                                                  target=MQTTClientSubscriber.run_latency_compute_thread)
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
                dequeued_message = MQTTClientSubscriber.message_queue[current_index]
                msg_rcvd_timestamp, msg = dequeued_message[0], dequeued_message[1]
                MQTTClientSubscriber.parse_message_and_compute_latency(msg, msg_rcvd_timestamp)
                current_index += 1
            except:
                logging.info("No more messages.")
                del MQTTClientSubscriber.message_queue
                MQTTClientSubscriber.message_queue = []
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
        self.connect()

    def cleanup(self):
        pass


if __name__ == '__main__':
    worker = MQTTClientSubscriber()
    MQTTClientSubscriber.continue_poll = True
    try:
        worker.perform_job()
    except KeyboardInterrupt:
        logging.error("Keyboard interrupt." + sys.exc_info()[0])
        logging.error("Exception in user code:")
        logging.error("-" * 60)
        traceback.print_exc(file=sys.stdout)
        logging.error("-" * 60)
        MQTTClientSubscriber.continue_poll = False
