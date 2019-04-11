import logging
import os
import sys
import threading
import time

import pulsar


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


class PulsarMsgQAPI:
    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None):
        if not is_producer and not is_consumer:
            logging.info("PulsarMsgQAPI{}: You need to pick either producer or consumer."
                         .format(thread_identifier))
            pass
        elif is_consumer and not subscription_cb:
            logging.error("PulsarMsgQAPI:{} You need to pass a subscription callback function."
                          .format(thread_identifier))
            pass
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.consumer_thread = None
        self.is_connected = False
        self.producer_instance = None
        self.consumer_instance = None
        self.publisher_topic = None
        self.subscriber_topic = None
        self.redis_instance = None
        self.client_instance = None
        self.broker_hostname = None
        self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.thread_identifier = thread_identifier
        self.__read_environment_variables()
        self.subscription_cb = subscription_cb
        self.connect()
        if self.is_consumer:
            self.create_consumer_thread()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while not self.broker_hostname:
            time.sleep(2)
            logging.info("PulsarMsgQAPI:{} "
                         "Trying to read the environment variables..."
                         .format(self.thread_identifier))
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="6650"))
            self.publisher_topic = os.getenv("publisher_topic_key", default=None)
            self.subscriber_topic = os.getenv("subscriber_topic_key", default=None)
        # if self.cont_id and len(self.cont_id) >= 12:
        #    self.topic += '_' + self.cont_id[:12]
        logging.info("PulsarMsgQAPI:{} broker_hostname={}"
                     .format(self.thread_identifier,
                             self.broker_hostname))
        logging.info("PulsarMsgQAPI:{} publisher_topic={}"
                     .format(self.thread_identifier,
                             self.publisher_topic))
        logging.info("PulsarMsgQAPI:{} subscriber_topic={}"
                     .format(self.thread_identifier,
                             self.subscriber_topic))
        logging.info("PulsarMsgQAPI:{} broker_port={}"
                     .format(self.thread_identifier,
                             self.broker_port))

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

        while not self.is_connected:
            try:
                self.client_instance = pulsar.Client('pulsar://{}:{}'
                                                     .format(self.broker_hostname,
                                                             self.broker_port))
                logging.info("{}: Successfully connected to {}:{}."
                             .format(self.thread_identifier,
                                     self.broker_hostname,
                                     self.broker_port))
                if self.is_producer:
                    self.producer_instance = \
                        self.client_instance.create_producer(self.publisher_topic)
                    logging.info("{}: Successfully created producer for topic {}."
                                 .format(self.thread_identifier,
                                         self.publisher_topic))

                self.is_connected = True

            except:
                logging.info("{}: Trying to connect to {}:{}."
                             .format(self.thread_identifier,
                                     self.broker_hostname,
                                     self.broker_port))
                time.sleep(5)

    def subscribe(self):
        self.consumer_instance = \
            self.client_instance.subscribe(self.subscriber_topic,
                                           'my-subscription')

    @staticmethod
    def run_consumer_thread(*args, **kwargs):
        logging.debug("Starting {}".format(threading.current_thread().getName()))
        consumer_instance = None
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'consumer_instance':
                consumer_instance = value
        t = threading.currentThread()
        consumer_instance.subscribe()
        while getattr(t, "do_run", True):
            consumer_instance.consume_message()
        logging.debug("Consumer {}: Exiting"
                      .format(threading.current_thread().getName()))

    def create_consumer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="consumer_thread",
                                                target=PulsarMsgQAPI.run_consumer_thread,
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
            self.client_instance.close()
        self.client_instance = None

    def consume_message(self):
        message = self.consumer_instance.receive()
        event_message = "\n \n Received message from topic: {},payload={}." \
            .format(self.subscriber_topic, message.data())
        logging.debug(event_message)
        self.redis_instance.write_an_event_in_redis_db(event_message)
        self.redis_instance.increment_dequeue_count()
        self.subscription_cb(message.data())
        self.consumer_instance.acknowledge(message)

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
        self.producer_instance.send(message.encode('utf-8'))
        self.redis_instance.increment_enqueue_count()
