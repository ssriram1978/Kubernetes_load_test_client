import logging
import os
import sys
import threading
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

from infrastructure_components.redis_client.redis_interface import RedisInterface


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
        self.consumer_thread = None
        self.is_connected = False
        self.publisher_topic = None
        self.subscriber_topic = None
        self.redis_instance = None
        self.client_instance = None
        self.broker_hostname = None
        self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.thread_identifier = thread_identifier
        self.__read_environment_variables()
        self.subscription_cb = subscription_cb
        if self.is_producer:
            self.connect()
        elif self.is_consumer:
            self.create_consumer_thread()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while not self.broker_hostname:
            time.sleep(2)
            logging.info("RabbitMsgQAPI:{} "
                         "Trying to read the environment variables..."
                         .format(self.thread_identifier))
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="1883"))
            self.publisher_topic = os.getenv("publisher_topic_key", default=None)
            self.subscriber_topic = os.getenv("subscriber_topic_key", default=None)
        # if self.cont_id and len(self.cont_id) >= 12:
        #    self.topic += '_' + self.cont_id[:12]
        logging.info("RabbitMsgQAPI:{} broker_hostname={}"
                     .format(self.thread_identifier,
                             self.broker_hostname))
        logging.info("RabbitMsgQAPI:{} publisher_topic={}"
                     .format(self.thread_identifier,
                             self.publisher_topic))
        logging.info("RabbitMsgQAPI:{} subscriber_topic={}"
                     .format(self.thread_identifier,
                             self.subscriber_topic))
        logging.info("RabbitMsgQAPI:{} broker_port={}"
                     .format(self.thread_identifier,
                             self.broker_port))

    def on_subscribe(self, client, userdata, mid, granted_qos):
        print("successfully subscribed.")
        logging.info("successfully subscribed.")

    def connect(self):
        """
        Connect to a broker.
        :return:
        """
        if self.is_producer:
            self.redis_instance = RedisInterface(self.thread_identifier)
            self.publish_topic_in_redis_db(self.publisher_topic)
        elif self.is_consumer:
            self.redis_instance = RedisInterface(self.thread_identifier)
            self.publish_topic_in_redis_db(self.subscriber_topic)

        self.client_instance = mqtt.Client()
        if self.is_consumer:
            while not self.is_connected:
                try:
                    self.client_instance.on_connect = self.on_connect
                    self.client_instance.on_message = self.on_message
                    self.client_instance.connect(self.broker_hostname, self.broker_port, 60)
                    self.client_instance.loop_forever(timeout=0.01,
                                                      max_packets=100,
                                                      retry_first_connection=False)
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

                except:
                    logging.info("{}: Trying to connect to {}:{}."
                                 .format(self.thread_identifier,
                                         self.broker_hostname,
                                         self.broker_port))
                    time.sleep(5)
        elif self.is_producer:
            while not self.is_connected:
                try:
                    self.client_instance.on_connect = self.on_connect
                    self.client_instance.connect(self.broker_hostname, self.broker_port, 60)
                    self.is_connected = True
                except:
                    logging.info("{}: Trying to connect to {}:{}."
                                 .format(self.thread_identifier,
                                         self.broker_hostname,
                                         self.broker_port))
                    time.sleep(5)
                    pass

    @staticmethod
    def run_consumer_thread(*args, **kwargs):
        logging.debug("Starting {}".format(threading.current_thread().getName()))
        consumer_instance = None
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'consumer_instance':
                consumer_instance = value
        t = threading.currentThread()
        consumer_instance.connect()
        while getattr(t, "do_run", True):
            time.sleep(1)
        logging.debug("Consumer {}: Exiting"
                      .format(threading.current_thread().getName()))

    def create_consumer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="consumer_thread",
                                                target=RabbitMsgQAPI.run_consumer_thread,
                                                args=(),
                                                kwargs={'consumer_instance':
                                                            self})
        self.consumer_thread.do_run = True
        self.consumer_thread.name = "consumer"
        self.consumer_thread.start()

    def publish_topic_in_redis_db(self, key_prefix):
        if self.cont_id and len(self.cont_id) >= 12:
            if self.is_producer:
                self.redis_instance.set_the_key_in_redis_db(key_prefix, self.publisher_topic)
            elif self.is_consumer:
                self.redis_instance.set_the_key_in_redis_db(key_prefix, self.subscriber_topic)
        else:
            key = key_prefix + '_' + self.cont_id[:12]
            if self.is_producer:
                self.redis_instance.set_the_key_in_redis_db(key, self.publisher_topic)
            elif self.is_consumer:
                self.redis_instance.set_the_key_in_redis_db(key, self.subscriber_topic)

    def disconnect(self):
        if self.client_instance:
            self.client_instance.disconnect()
        self.client_instance = None

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
            logging.info("Trying to subscribe to topic {} at broker {}:{}."
                         .format(self.subscriber_topic,
                                 self.broker_hostname,
                                 self.broker_port))
            self.client_instance.on_message = self.on_message
            self.client_instance.on_subscribe = self.on_subscribe
            client.subscribe(self.subscriber_topic)

    def on_message(self, client, userdata, message):
        event_message = "\n \n Received message from topic: {},payload={}." \
            .format(message.topic, message.payload)
        logging.debug(event_message)
        self.redis_instance.write_an_event_in_redis_db(event_message)
        self.redis_instance.increment_dequeue_count()
        self.subscription_cb(message.payload)
        self.client_instance.on_message = self.on_message

    def get_topic_name(self):
        if self.is_producer:
            return self.publisher_topic
        elif self.is_consumer:
            return self.subscriber_topic
        else:
            return None

    def cleanup(self):
        if self.consumer_thread:
            self.client_instance.disconnect()
            if getattr(self.consumer_thread, "do_run", True):
                self.consumer_thread.do_run = False
                time.sleep(5)
                logging.debug("Trying to join thread {}."
                              .format(self.consumer_thread.getName()))
                self.consumer_thread.join(1.0)

    def publish(self, message):
        """
        This method tries to post a message to the pre-defined topic.
        :param message:
        :return status False or True:
        """

        event_message = "\n \n {}: Publishing a message {} to topic {}." \
            .format(self.thread_identifier,
                    message,
                    self.publisher_topic)
        logging.debug(event_message)
        self.redis_instance.write_an_event_in_redis_db(event_message)
        self.client_instance.publish(self.publisher_topic, message)
        self.redis_instance.increment_enqueue_count()
