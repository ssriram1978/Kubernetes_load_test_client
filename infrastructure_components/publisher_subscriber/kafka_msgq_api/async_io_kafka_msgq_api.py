import json
import logging
import os
import sys
import threading
import time
import traceback
from pprint import pformat

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio

# sys.path.append("..")  # Adds higher directory to python modules path.

loop = asyncio.get_event_loop()


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


def stats_cb(stats_json_str):
    stats_json = json.loads(stats_json_str)
    print('\nKAFKA Stats: {}\n'.format(pformat(stats_json)))


def print_assignment(consumer, partitions):
    logging.info('consumer = {}, Assignment {}:'.format(consumer, partitions))


class AsyncIOKafkaMsgQAPI(object):
    """
    This class provides API's into interact with Kafka Queue.
    """

    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None,
                 queue_name=None):
        if not is_producer and not is_consumer:
            logging.error("AsyncIOKafkaMsgQAPI: You need to pick either producer or consumer.")
            pass
        elif is_consumer and not subscription_cb:
            logging.error("AsyncIOKafkaMsgQAPI: You need to pass a subscription callback function.")
            pass
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.producer_instance = None
        self.consumer_instance = None
        self.broker_hostname = None
        self.broker_port = None
        # self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.cont_id = os.popen("cat /etc/hostname").read()
        self.cont_id = self.cont_id[:-1]
        self.publisher_topic = None
        self.redis_instance = None
        if self.is_producer:
            self.publisher_topic = queue_name
        self.subscriber_topic = None
        if self.is_consumer:
            self.subscriber_topic = queue_name
        self.producer_conf = None
        self.consumer_conf = None
        self.partitions_per_topic = 10
        self.is_topic_created = True  # Do not try to create a topic in the zookeeper.
        self.subscription_cb = None
        self.consumer_thread = None
        self.is_producer_connected = False
        self.is_consumer_connected = False
        self.thread_identifier = thread_identifier
        self.redis_instance = RedisInterface(self.thread_identifier)
        self.__read_environment_variables()
        if is_producer:
            self.create_producer_thread()
        elif is_consumer:
            self.subscription_cb = subscription_cb
            self.create_consumer_thread()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while not self.broker_hostname:
            time.sleep(2)
            logging.info("AsyncIOKafkaMsgQAPI: "
                         "Trying to read the environment variables...")
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="9092"))

        logging.info("AsyncIOKafkaMsgQAPI: broker_hostname={}".format(self.broker_hostname))
        logging.info("AsyncIOKafkaMsgQAPI: broker_port={}".format(self.broker_port))
        logging.info("AsyncIOKafkaMsgQAPI: publisher_topic={}".format(self.publisher_topic))
        logging.info("AsyncIOKafkaMsgQAPI: subscriber_topic={}".format(self.subscriber_topic))

    @staticmethod
    def enable_logging(logger_name):
        # Create logger for consumer (logs will be emitted when poll() is called)
        pass

    # Optional per-message delivery callback (triggered by poll() or flush())
    # when a message has been successfully delivered or permanently
    # failed delivery (after retries).
    @staticmethod
    def delivery_callback(err, msg):
        if err:
            logging.error('%% Message failed delivery: %s\n' % err)
        else:
            logging.error('%% Message delivered to %s [%d] @ %s\n' %
                          (msg.topic(), msg.partition(), str(msg.offset())))

    def producer_connect(self):
        """
        This method tries to connect to the kafka broker based upon the type of kafka.
        :return:
        """
        while not self.is_producer_connected:
            try:
                self.producer_instance = AIOKafkaProducer(
                    loop=loop,
                    bootstrap_servers='{}:{}'.format(self.broker_hostname, self.broker_port))
                self.is_producer_connected = True
                # Get cluster layout and initial topic/partition leadership information
                await self.producer_instance.start()
            except:
                print("Exception in user code:")
                print("-" * 60)
                traceback.print_exc(file=sys.stdout)
                print("-" * 60)
                time.sleep(5)
            else:
                logging.info("AsyncIOKafkaMsgQAPI: Successfully "
                             "connected to broker={}:{}"
                             .format(self.broker_hostname, self.broker_port))

    def publish(self, message):
        """
        This method tries to post a message to the pre-defined kafka topic.
        :param message:
        :return status False or True:
        """
        status = False

        if message is None or len(message) == 0:
            logging.info("AsyncIOKafkaMsgQAPI: filename is None or invalid")
            return status

        if not self.is_producer_connected:
            self.producer_connect()

        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.

        event_message = "AsyncIOKafkaMsgQAPI: Posting filename={} into kafka broker={}, topic={}" \
            .format(message,
                    self.broker_hostname,
                    self.publisher_topic)
        logging.debug(event_message)

        value = message.encode('utf-8')
        try:
            # Produce line (without newline)
            self.redis_instance.write_an_event_in_redis_db(event_message)
            # Produce message
            await self.producer_instance.send_and_wait(self.publisher_topic, value)
            self.redis_instance.increment_enqueue_count()
            status = True
        except BufferError:
            logging.error('%% Local producer queue is full '
                          '(%d messages awaiting delivery): try again\n' %
                          len(self.producer_instance))
            status = False
        except:
            print("AsyncIOKafkaMsgQAPI: Exception in user code:")
            print("-" * 60)
            traceback.print_exc(file=sys.stdout)
            print("-" * 60)
            status = False
        else:
            event = "AsyncIOKafkaMsgQAPI: Posting message={} into " \
                    "kafka broker={}, topic={}." \
                .format(message,
                        self.broker_hostname,
                        self.publisher_topic)
        finally:
            # Wait for all pending messages to be delivered or expire.
            await self.producer_instance.stop()
            return status

    def consumer_connect(self):
        """
        This method tries to connect to the kafka broker.
        :return:
        """
        while not self.is_consumer_connected:
            try:
                logging.info("Consumer:{}:Trying to connect to broker_hostname={}:{}"
                             .format(self.thread_identifier,
                                     self.broker_hostname,
                                     self.broker_port))

                # Create Consumer instance
                self.consumer_instance = AIOKafkaConsumer(
                    self.subscriber_topic,
                    loop=loop,
                    group_id="kafka-consumer",
                    bootstrap_servers='{}:{}'.format(self.broker_hostname, self.broker_port),
                    auto_offset_reset='earliest')

                logging.info("Consumer:{}:Consumer Successfully "
                             "connected to broker_hostname={}"
                             .format(self.thread_identifier,
                                     self.broker_hostname))
                self.is_consumer_connected = True
            except:
                logging.info("Consumer:{}:Exception in user code:"
                             .format(self.thread_identifier))
                logging.info("-" * 60)
                traceback.print_exc(file=sys.stdout)
                logging.info("-" * 60)
                time.sleep(5)

    @staticmethod
    def process_subscriber_message(consumer_instance, msg):
        logging.debug("msg={}".format(msg))
        consumer_instance.redis_instance.increment_dequeue_count()
        if msg.find("metadata=") == -1:
            consumer_instance.subscription_cb(msg)
        else:
            # This is from SNAPLOGIC which adds extra headers. Skip them.
            value_index = msg.find("value=")
            if value_index:
                value_index += len("value=")
                msg = msg[value_index:-1]
                logging.debug("post-formatted msg={}".format(msg))
                consumer_instance.subscription_cb(msg)

    @staticmethod
    def run_producer_thread(*args, **kwargs):
        logging.info("Starting {}".format(threading.current_thread().getName()))
        producer_instance = None
        for name, value in kwargs.items():
            logging.info("name={},value={}".format(name, value))
            if name == 'producer_instance':
                producer_instance = value
        t = threading.currentThread()
        producer_instance.producer_connect()
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                loop.run_until_complete(producer_instance.producer.stop())
            except:
                logging.debug("Exception occurred when trying to poll a kafka topic.")
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))
        loop.close()

    def create_producer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="producer_thread",
                                                target=AsyncIOKafkaMsgQAPI.run_producer_thread,
                                                args=(),
                                                kwargs={'producer_instance':
                                                            self})
        self.consumer_thread.do_run = True
        self.consumer_thread.name = "consumer"
        self.consumer_thread.start()

    @staticmethod
    def run_consumer_thread(*args, **kwargs):
        logging.info("Starting {}".format(threading.current_thread().getName()))
        consumer_instance = None
        for name, value in kwargs.items():
            logging.info("name={},value={}".format(name, value))
            if name == 'consumer_instance':
                consumer_instance = value
        t = threading.currentThread()
        consumer_instance.consumer_connect()
        logging.info("Trying to consume messages from {}.".format(consumer_instance.subscriber_topic))
        loop.run_until_complete(consumer_instance.consumer.stop())
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                msg = loop.run_until_complete(consumer_instance.consumer.getone())
                if msg:
                    msg = msg[0].value.decode('utf-8')
                    AsyncIOKafkaMsgQAPI.process_subscriber_message(consumer_instance, msg)
            except:
                logging.debug("Exception occurred when trying to poll a kafka topic.")
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))
        loop.close()

    def create_consumer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="consumer_thread",
                                                target=AsyncIOKafkaMsgQAPI.run_consumer_thread,
                                                args=(),
                                                kwargs={'consumer_instance':
                                                            self})
        self.consumer_thread.do_run = True
        self.consumer_thread.name = "consumer"
        self.consumer_thread.start()

    @staticmethod
    def subscription_partition_assignment_cb(consumer, partitions):
        logging.info('subscription_partition_assignment_cb: '
                     'consumer = {}, Assignment {}:'.format(consumer, partitions))

    @staticmethod
    def subscription_partition_revoke_cb(consumer, partitions):
        logging.info('subscription_partition_revoke_cb: '
                     'consumer = {}, Assignment {}:'.format(consumer, partitions))

    def get_topic_name(self):
        if self.is_producer:
            return self.publisher_topic
        elif self.is_consumer:
            return self.subscriber_topic
        else:
            return None

    def disconnect(self):
        if self.consumer_instance:
            self.consumer_instance.close()
        self.consumer_instance = None

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

    def cleanup(self):
        if self.consumer_thread:
            self.consumer_instance.close()
            if getattr(self.consumer_thread, "do_run", True):
                self.consumer_thread.do_run = False
                time.sleep(5)
                logging.info("Trying to join thread {}."
                             .format(self.consumer_thread.getName()))
                self.consumer_thread.join(1.0)
