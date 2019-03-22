import logging
import os
import sys
import time

import paho.mqtt.client as mqtt


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


class RabbitMsgQAPI:
    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None):
        if not is_producer and not is_consumer:
            logging.info("RabbitMsgQAPI: You need to pick either producer or consumer.")
            pass
        elif is_consumer and not subscription_cb:
            logging.error("ConfluentKafkaMsgQAPI: You need to pass a subscription callback function.")
            pass
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.client_instance = None
        self.broker_hostname = None
        self.topic = None
        self.is_topic_created = False
        self.subscription_cb = None
        self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.thread_identifier = thread_identifier
        self.__read_environment_variables()
        self.connect()
        if is_consumer:
            self.subscription_cb = subscription_cb

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while self.broker_hostname is None or \
                self.topic is None:
            time.sleep(2)
            logging.info("RabbitMsgQAPI: "
                         "Trying to read the environment variables...")
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="1883"))
            self.topic = os.getenv("topic_key", default=None)
        self.topic += '_' + self.cont_id[:12]
        logging.info("RabbitMsgQAPI: broker_hostname={}".format(self.broker_hostname))
        logging.info("RabbitMsgQAPI: topic={}".format(self.topic))
        logging.info("RabbitMsgQAPI: broker_port={}".format(self.broker_port))

    def connect(self):
        """
        Connect to a broker.
        :return:
        """
        self.client_instance = mqtt.Client()
        self.client_instance.on_connect = self.on_connect
        self.client_instance.on_message = self.subscription_cb
        is_connected = False
        while not is_connected:
            try:
                self.client_instance.connect(self.broker_hostname, self.broker_port, 60)
                logging.info("Successfully connected to {}:{}".format(self.broker_hostname, self.broker_port))
                is_connected = True
            except:
                logging.error("Unable to connect to {}:{}".format(self.broker_hostname, self.broker_port))
                time.sleep(5)
        if self.is_producer:
            self.client_instance.loop_forever()

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
        if self.is_consumer:
            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            self.client_instance.subscribe(self.topic)

    def get_topic_name(self):
        return self.topic

    def publish(self, message):
        """
        This method tries to post a message to the pre-defined topic.
        :param message:
        :return status False or True:
        """
        self.client_instance.publish(message)