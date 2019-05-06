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

from infrastructure_components.publisher_subscriber.rabbit_msgq_api.rabbit_msgq_api import RabbitMsgQAPI
from infrastructure_components.publisher_subscriber.confluent_kafka_msgq_api.confluent_kafka_msgq_api import \
    ConfluentKafkaMsgQAPI
from infrastructure_components.publisher_subscriber.wurstmeister_kafka_msgq_api.wurstmeister_kafka_msgq_api import \
    WurstMeisterKafkaMsgQAPI
from infrastructure_components.publisher_subscriber.pulsar_msgq_api.pulsar_msgq_api import \
    PulsarMsgQAPI
from infrastructure_components.publisher_subscriber.nats_msgq_api.nats_msgq_api import \
    NatsMsgQAPI
from infrastructure_components.publisher_subscriber.zeromq_api.zeromq_api import \
    ZeroMsgQAPI
from infrastructure_components.redis_client.redis_interface import RedisInterface


class PublisherSubscriberAPI:
    """
    This is a factory design pattern.
    This class produces messages into
    1. Kafka Queue.
    2. Rabbit Message Queue.
    3. Pulsar Message Queue.
    """
    rabbitMsgQType = "RabbitMQ"
    confluentKafkaMsgQType = "ConfluentKafka"
    wurstmeisterKafakMsqQType = "WurstMeisterKafka"
    pulsarMsgQType = "Pulsar"
    natsMsgQType = "NATS"
    zeroMQType = "ZeroMQ"

    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None):
        self.message_queue_instance = None
        self.hash_table_name = None
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.subscription_cb = subscription_cb
        self.type_of_messaging_queue = None
        self.container_id = os.popen("cat /etc/hostname").read()
        self.container_id = self.container_id[:-1]
        self.thread_identifier = thread_identifier
        self.dict_of_queue_names = None
        self.redis_instance = RedisInterface("Publisher_Subscriber")
        self.read_environment_variables()
        self.__connect()

    def read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while not self.type_of_messaging_queue or \
                not self.hash_table_name:
            time.sleep(2)
            logging.info("PublisherSubscriberAPI:{} "
                         "Trying to read the environment variables..."
                         .format(self.thread_identifier))
            self.type_of_messaging_queue = os.getenv("type_of_messaging_queue_key",
                                                     default=None)
            self.hash_table_name = os.getenv("hash_table_name",
                                             default=None)
        logging.info("PublisherSubscriberAPI:{}\n"
                     "hash_table_name:{}\n"
                     "type_of_messaging_queue={}.\n"
                     .format(self.thread_identifier,
                             self.hash_table_name,
                             self.type_of_messaging_queue))

    def fetch_queue_name_from_redis(self):
        queue_name_fetched = False
        while not queue_name_fetched:
            if self.redis_instance:
                try:
                    dict_str = self.redis_instance.get_list_of_values_based_upon_a_key(
                        self.hash_table_name,
                        self.container_id)[0].decode('utf-8')
                    if dict_str:
                        logging.info("Found value = {} for key {} in hash table {}."
                                     .format(dict_str,
                                             self.container_id,
                                             self.hash_table_name))
                        self.dict_of_queue_names = eval(dict_str)
                        queue_name_fetched = True
                except:
                    logging.info("Unable to find a key {} in hash table {}."
                                 .format(self.container_id,
                                         self.hash_table_name))
                    time.sleep(1)

    def __connect(self):
        """
        This method tries to connect to the messaging queue.
        :return:
        """
        if self.message_queue_instance is None:
            queue_name = None
            self.fetch_queue_name_from_redis()
            if self.is_producer:
                queue_name = self.dict_of_queue_names["publisher"]
                logging.info("Found publisher queue name {}.".format(queue_name))
            elif self.is_consumer:
                queue_name = self.dict_of_queue_names["subscriber"]
                logging.info("Found subscriber queue name {}.".format(queue_name))
            try:
                if self.type_of_messaging_queue == PublisherSubscriberAPI.rabbitMsgQType:
                    self.message_queue_instance = RabbitMsgQAPI(is_producer=self.is_producer,
                                                                is_consumer=self.is_consumer,
                                                                thread_identifier=self.thread_identifier,
                                                                subscription_cb=self.subscription_cb,
                                                                queue_name=queue_name)
                elif self.type_of_messaging_queue == PublisherSubscriberAPI.confluentKafkaMsgQType:
                    self.message_queue_instance = ConfluentKafkaMsgQAPI(is_producer=self.is_producer,
                                                                        is_consumer=self.is_consumer,
                                                                        thread_identifier=self.thread_identifier,
                                                                        subscription_cb=self.subscription_cb)
                elif self.type_of_messaging_queue == PublisherSubscriberAPI.wurstmeisterKafakMsqQType:
                    self.message_queue_instance = WurstMeisterKafkaMsgQAPI(is_producer=self.is_producer,
                                                                           is_consumer=self.is_consumer,
                                                                           thread_identifier=self.thread_identifier,
                                                                           subscription_cb=self.subscription_cb,
                                                                           queue_name=queue_name)
                elif self.type_of_messaging_queue == PublisherSubscriberAPI.pulsarMsgQType:
                    self.message_queue_instance = PulsarMsgQAPI(is_producer=self.is_producer,
                                                                is_consumer=self.is_consumer,
                                                                thread_identifier=self.thread_identifier,
                                                                subscription_cb=self.subscription_cb,
                                                                queue_name=queue_name)
                elif self.type_of_messaging_queue == PublisherSubscriberAPI.natsMsgQType:
                    self.message_queue_instance = NatsMsgQAPI(is_producer=self.is_producer,
                                                              is_consumer=self.is_consumer,
                                                              thread_identifier=self.thread_identifier,
                                                              subscription_cb=self.subscription_cb,
                                                              queue_name=queue_name)

                elif self.type_of_messaging_queue == PublisherSubscriberAPI.zeroMQType:
                    self.message_queue_instance = ZeroMsgQAPI(is_producer=self.is_producer,
                                                              is_consumer=self.is_consumer,
                                                              thread_identifier=self.thread_identifier,
                                                              subscription_cb=self.subscription_cb,
                                                              queue_name=queue_name)

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
