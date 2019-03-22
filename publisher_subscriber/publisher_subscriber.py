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
from redis_client.redis_interface import RedisInterface


class ProduceConsumeAPI:
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
                 type_of_messaging_queue=None,
                 thread_identifier=None,
                 subscription_cb=None):
        self.message_queue_instance = None
        self.redis_instance = None
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.subscription_cb = subscription_cb
        self.type_of_messaging_queue = type_of_messaging_queue
        self.thread_identifier = thread_identifier
        self.read_environment_variables()
        # self.__connect()

    def read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while self.type_of_messaging_queue is None:
            time.sleep(2)
            logging.info("ProduceConsumeAPI: "
                         "Trying to read the environment variables...")
            self.type_of_messaging_queue = os.getenv("type_of_messaging_queue_key",
                                                     default=None)
        logging.info("ProduceConsumeAPI:"
                     "type_of_messaging_queue={}"
                     .format(self.type_of_messaging_queue))

    def __connect(self):
        """
        This method tries to connect to the messaging queue.
        :return:
        """
        if self.message_queue_instance is None:
            try:
                if self.type_of_messaging_queue == ProduceConsumeAPI.rabbitMsgQType:
                    self.message_queue_instance = RabbitMsgQAPI(is_producer=self.is_producer,
                                                                is_consumer=self.is_consumer,
                                                                thread_identifier=self.thread_identifier,
                                                                subscription_cb=self.subscription_cb)
                elif self.type_of_messaging_queue == ProduceConsumeAPI.confluentKafkaMsgQType:
                    self.message_queue_instance = ConfluentKafkaMsgQAPI(is_producer=self.is_producer,
                                                                        is_consumer=self.is_consumer,
                                                                        thread_identifier=self.thread_identifier,
                                                                        subscription_cb=self.subscription_cb)
                if not self.redis_instance:
                    if self.is_producer:
                        self.redis_instance = RedisInterface("Producer{}".format(self.thread_identifier))
                        self.publish_topic_in_redis_db('Producer')
                    elif self.is_consumer:
                        self.redis_instance = RedisInterface("Consumer{}".format(self.thread_identifier))
                        self.publish_topic_in_redis_db('Consumer')
            except:
                print("Exception in user code:")
                print("-" * 60)
                traceback.print_exc(file=sys.stdout)
                print("-" * 60)
                time.sleep(5)
            else:
                logging.info("ProduceConsumeAPI: Successfully "
                             "created producer instance for messageQ type ={}"
                             .format(self.type_of_messaging_queue))

    def publish_topic_in_redis_db(self, key_prefix):
        cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        key = key_prefix + '_' + cont_id[:12]
        value = self.message_queue_instance.get_topic_name()
        self.redis_instance.set_the_key_in_redis_db(key, value)

    def publish(self, message):
        """
        This method tries to post a message.
        :param message:
        :return True or False:
        """
        status = False

        if message is None or len(message) == 0:
            logging.info("filename is None or invalid")
            return status

        if self.message_queue_instance is None:
            self.__connect()

        if hasattr(self.message_queue_instance, 'publish'):
            status = self.message_queue_instance.publish(message)
            event = "Producer: Successfully posted a message = {} into msgQ. Status={}".format(message, status)
            self.redis_instance.write_an_event_in_redis_db(event)
            self.redis_instance.increment_enqueue_count()

        return status

    def subscribe(self):
        """
        This method tries to post a message.
        :return Freezes the current context and yeilds a message:
        Please make sure to iterate this over to unfreeze the context.
        """
        if self.message_queue_instance is None:
            self.__connect()
        if hasattr(self.message_queue_instance, 'subscribe'):
            self.message_queue_instance.subscribe()
            event = "Producer: Successfully subscribed."
            self.redis_instance.write_an_event_in_redis_db(event)

    self.redis_instance.increment_dequeue_count()
    self.redis_instance.write_an_event_in_redis_db("Consumer {}: Dequeued Message = {}"
                                                   .format(self.thread_identifier,
                                                           msg))

    def get_topic_name(self):
        return self.message_queue_instance.get_topic_name()

    def cleanup(self):
        if self.message_queue_instance:
            self.message_queue_instance.cleanup()
            self.message_queue_instance = None
