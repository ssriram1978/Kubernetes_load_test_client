import logging
import os
import sys
import time
import traceback


# sys.path.append("..")  # Adds higher directory to python modules path.

def import_all_modules():
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


import_all_modules()

from publisher_subscriber.rabbit_msgq_api.rabbit_msgq_api import RabbitMsgQAPI
from publisher_subscriber.confluent_kafka_msgq_api.confluent_kafka_msgq_api import \
    ConfluentKafkaMsgQAPI


class PublisherSubscriberAPI:
    """
    This is a factory design pattern.
    This class produces messages into
    1. Kafka Queue.
    2. Rabbit Message Queue.
    """
    rabbitMsgQType = "RabbitMQ"
    confluentKafkaMsgQType = "ConfluentKafka"

    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None):
        self.message_queue_instance = None
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.subscription_cb = subscription_cb
        self.type_of_messaging_queue = None
        self.thread_identifier = thread_identifier
        self.read_environment_variables()
        self.__connect()

    def read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while self.type_of_messaging_queue is None:
            time.sleep(2)
            logging.info("PublisherSubscriberAPI:{} "
                         "Trying to read the environment variables..."
                         .format(self.thread_identifier))
            self.type_of_messaging_queue = os.getenv("type_of_messaging_queue_key",
                                                     default=None)
        logging.info("PublisherSubscriberAPI:{}"
                     "type_of_messaging_queue={}"
                     .format(self.thread_identifier,
                             self.type_of_messaging_queue))

    def __connect(self):
        """
        This method tries to connect to the messaging queue.
        :return:
        """
        if self.message_queue_instance is None:
            try:
                if self.type_of_messaging_queue == PublisherSubscriberAPI.rabbitMsgQType:
                    self.message_queue_instance = RabbitMsgQAPI(is_producer=self.is_producer,
                                                                is_consumer=self.is_consumer,
                                                                thread_identifier=self.thread_identifier,
                                                                subscription_cb=self.subscription_cb)
                elif self.type_of_messaging_queue == PublisherSubscriberAPI.confluentKafkaMsgQType:
                    self.message_queue_instance = ConfluentKafkaMsgQAPI(is_producer=self.is_producer,
                                                                        is_consumer=self.is_consumer,
                                                                        thread_identifier=self.thread_identifier,
                                                                        subscription_cb=self.subscription_cb)
            except:
                print("Exception in user code:")
                print("-" * 60)
                traceback.print_exc(file=sys.stdout)
                print("-" * 60)
                time.sleep(5)
            else:
                logging.info("PublisherSubscriberAPI:{} Successfully "
                             "created instance for messageQ type ={}"
                             .format(self.thread_identifier,
                                     self.type_of_messaging_queue))

    def publish_topic_in_redis_db(self, key_prefix):
        if hasattr(self.message_queue_instance, 'publish_topic_in_redis_db'):
            self.message_queue_instance.publish_topic_in_redis_db(key_prefix)

    def publish(self, message):
        """
        This method tries to post a message.
        :param message:
        :return True or False:
        """
        status = False

        if hasattr(self.message_queue_instance, 'publish'):
            status = self.message_queue_instance.publish(message)

        return status

    def get_topic_name(self):
        return self.message_queue_instance.get_topic_name()

    def cleanup(self):
        if self.message_queue_instance:
            self.message_queue_instance.cleanup()
            self.message_queue_instance = None
