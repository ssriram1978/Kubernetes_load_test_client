import logging
import os
import sys
import time

import paho.mqtt.client as mqtt

from redis_client.redis_interface import RedisInterface


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
            logging.info("RabbitMsgQAPI{}: You need to pick either producer or consumer."
                         .format(thread_identifier))
            pass
        elif is_consumer and not subscription_cb:
            logging.error("RabbitMsgQAPI:{} You need to pass a subscription callback function."
                          .format(thread_identifier))
            pass
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.is_connected = False
        self.redis_instance = None
        self.client_instance = None
        self.broker_hostname = None
        self.topic = None
        self.subscription_cb = None
        self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.thread_identifier = thread_identifier
        self.__read_environment_variables()
        if is_consumer:
            self.subscription_cb = subscription_cb
        self.connect()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while self.broker_hostname is None or \
                self.topic is None:
            time.sleep(2)
            logging.info("RabbitMsgQAPI:{} "
                         "Trying to read the environment variables..."
                         .format(self.thread_identifier))
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="1883"))
            self.topic = os.getenv("topic_key", default=None)
        if self.cont_id and len(self.cont_id) >= 12:
            self.topic += '_' + self.cont_id[:12]
        logging.info("RabbitMsgQAPI:{} broker_hostname={}"
                     .format(self.thread_identifier,
                             self.broker_hostname))
        logging.info("RabbitMsgQAPI:{} topic={}"
                     .format(self.thread_identifier,
                             self.topic))
        logging.info("RabbitMsgQAPI:{} broker_port={}"
                     .format(self.thread_identifier,
                             self.broker_port))

    def connect(self):
        """
        Connect to a broker.
        :return:
        """
        if self.is_producer:
            self.redis_instance = RedisInterface(self.thread_identifier)
            self.publish_topic_in_redis_db(self.topic)
        elif self.is_consumer:
            self.redis_instance = RedisInterface(self.thread_identifier)
            self.publish_topic_in_redis_db(self.topic)

        self.client_instance = mqtt.Client()
        self.client_instance.on_connect = self.on_connect
        self.client_instance.on_message = self.on_message
        self.client_instance.connect_async(self.broker_hostname, self.broker_port, 60)
        self.client_instance.loop_start()

        while not self.is_connected:
            logging.info("{}: Trying to connect to {}:{}."
                         .format(self.thread_identifier,
                                 self.broker_hostname,
                                 self.broker_port))
            time.sleep(5)

        logging.info("{}: Successfully connected to {}:{}"
                     .format(self.thread_identifier,
                             self.broker_hostname,
                             self.broker_port))

    def on_subscribed(self):
        logging.info("{}: successfully subscribed to topic = {}"
                     .format(self.thread_identifier,
                             self.topic))

    def publish_topic_in_redis_db(self, key_prefix):
        if self.cont_id and len(self.cont_id) >= 12:
            self.redis_instance.set_the_key_in_redis_db(key_prefix, self.topic)
        else:
            key = key_prefix + '_' + self.cont_id[:12]
            self.redis_instance.set_the_key_in_redis_db(key, self.topic)

    def on_connect(self, client, userdata, flags, rc):
        """
        The callback for when the client receives a CONNACK response from the server.
        :param client:
        :param userdata:
        :param flags:
        :param rc:
        :return:
        """
        self.is_connected = True

        logging.debug("{}:Connected with result code {}".format(self.thread_identifier,
                                                                str(rc)))
        if self.is_consumer:
            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            logging.info("{}: Subscribing to topic {}."
                         .format(self.thread_identifier,
                                 self.topic))

            self.client_instance.on_subscribe = self.on_subscribed
            self.client_instance.on_message = self.on_message
            self.client_instance.subscribe(self.topic)

    def on_message(self, client, userdata, message):
        message_string = '{} Received message {} on topic {} with QOS {}.' \
            .format(self.thread_identifier,
                    message.payload,
                    message.topic,
                    str(message.qos))

        logging.info(message_string)
        self.subscription_cb(message.payload)
        self.client_instance.on_message = self.on_message
        self.redis_instance.increment_dequeue_count()


def get_topic_name(self):
    return self.topic


def cleanup(self):
    pass


def publish(self, message):
    """
    This method tries to post a message to the pre-defined topic.
    :param message:
    :return status False or True:
    """
    event = "{}: Successfully posted a message = {} into topic {}." \
        .format(self.thread_identifier,
                message,
                self.topic)
    self.redis_instance.write_an_event_in_redis_db(event)
    self.redis_instance.increment_enqueue_count()
    logging.debug("{}: Publishing message {} to topic {}."
                  .format(self.thread_identifier,
                          message,
                          self.topic))
    self.client_instance.publish(message)
