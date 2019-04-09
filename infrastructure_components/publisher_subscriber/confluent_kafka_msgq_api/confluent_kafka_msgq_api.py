import json
import logging
import os
import sys
import threading
import time
import traceback
from pprint import pformat

from confluent_kafka import Producer, Consumer, KafkaException, admin


# sys.path.append("..")  # Adds higher directory to python modules path.

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


class ConfluentKafkaMsgQAPI(object):
    """
    This class provides API's into interact with Kafka Queue.
    """

    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None):
        if not is_producer and not is_consumer:
            logging.error("ConfluentKafkaMsgQAPI: You need to pick either producer or consumer.")
            pass
        elif is_consumer and not subscription_cb:
            logging.error("ConfluentKafkaMsgQAPI: You need to pass a subscription callback function.")
            pass

        self.producer_instance = None
        self.consumer_instance = None
        self.broker_hostname = None
        self.broker_port = None
        # self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.cont_id = None
        self.redis_instance = None
        self.topic = None
        self.producer_conf = None
        self.consumer_conf = None
        self.is_topic_created = False
        self.subscription_cb = None
        self.consumer_thread = None
        self.thread_identifier = thread_identifier
        self.redis_instance = RedisInterface(self.thread_identifier)
        self.__read_environment_variables()
        if is_producer:
            self.__producer_connect()
            self.__create_topic()
        elif is_consumer:
            self.subscription_cb = subscription_cb
            self.create_consumer_thread()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while self.broker_hostname is None or \
                self.topic is None:
            time.sleep(2)
            logging.info("ConfluentKafkaMsgQAPI: "
                         "Trying to read the environment variables...")
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="9092"))
            self.topic = os.getenv("topic_key", default=None)
        logging.info("ConfluentKafkaMsgQAPI: broker_hostname={}".format(self.broker_hostname))
        logging.info("ConfluentKafkaMsgQAPI: broker_port={}".format(self.broker_port))
        logging.info("ConfluentKafkaMsgQAPI: topic={}".format(self.topic))

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

    def __producer_connect(self):
        """
        This method tries to connect to the kafka broker based upon the type of kafka.
        :return:
        """
        is_connected = False
        if self.producer_instance is None:
            try:
                ConfluentKafkaMsgQAPI.enable_logging('ConfluentKafkaMsgQAPI:producer')
                self.producer_conf = {'bootstrap.servers': '{}:{}'
                    .format(self.broker_hostname, self.broker_port)}
                # Create Producer instance
                self.producer_instance = Producer(**self.producer_conf)
                is_connected = True
            except:
                print("Exception in user code:")
                print("-" * 60)
                traceback.print_exc(file=sys.stdout)
                print("-" * 60)
                time.sleep(5)
            else:
                logging.info("ConfluentKafkaMsgQAPI: Successfully "
                             "connected to broker={}:{}"
                             .format(self.broker_hostname, self.broker_port))
        return is_connected

    def __create_topic(self):
        if not self.is_topic_created:
            try:
                if self.producer_instance.list_topics(self.topic,
                                                      timeout=1.0):
                    logging.info("Found topic name = {} in the zookeeper."
                                 .format(self.topic))
                    self.is_topic_created = True
            except KafkaException:
                kafka_admin_client = admin.AdminClient(self.producer_conf)
                # cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
                # self.topic += '_' + cont_id[:12]
                logging.info("Creating topic {}."
                             .format(self.topic))
                ret = kafka_admin_client.create_topics(new_topics=[admin.NewTopic(topic=self.topic,
                                                                                  num_partitions=1)],
                                                       operation_timeout=1.0)
                logging.info("ret = {}".format(ret))

    def publish(self, message):
        """
        This method tries to post a message to the pre-defined kafka topic.
        :param message:
        :return status False or True:
        """
        status = False

        if message is None or len(message) == 0:
            logging.info("ConfluentKafkaMsgQAPI: filename is None or invalid")
            return status

        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.

        event_message = "ConfluentKafkaMsgQAPI: Posting filename={} into kafka broker={}, topic={}" \
            .format(message,
                    self.broker_hostname,
                    self.topic)
        logging.info(event_message)

        value = message.encode('utf-8')
        try:
            # Produce line (without newline)
            self.redis_instance.write_an_event_in_redis_db(event_message)
            self.producer_instance.produce(self.topic,
                                           value)
            self.redis_instance.increment_enqueue_count()
            status = True
        except BufferError:
            sys.stderr.write('%% Local producer queue is full '
                             '(%d messages awaiting delivery): try again\n' %
                             len(self.producer_instance))
            status = False
        except:
            print("ConfluentKafkaMsgQAPI: Exception in user code:")
            print("-" * 60)
            traceback.print_exc(file=sys.stdout)
            print("-" * 60)
            status = False
        else:
            event = "ConfluentKafkaMsgQAPI: Posting message={} into " \
                    "kafka broker={}, topic={}." \
                .format(message,
                        self.broker_hostname,
                        self.topic)
            # logging.info(event)
            # Wait for any outstanding messages to be delivered and delivery report
            # callbacks to be triggered.
            # Serve delivery callback queue.
            # NOTE: Since produce() is an asynchronous API this poll() call
            #       will most likely not serve the delivery callback for the
            #       last produce()d message.
            # self.producer_instance.poll(timeout=0.1)
            # Wait until all messages have been delivered
            # sys.stderr.write('%% Waiting for %d deliveries\n' % len(self.producer_instance))
            # self.producer_instance.flush(timeout=0.1)

            return status

    def consumer_connect(self):
        """
        This method tries to connect to the kafka broker.
        :return:
        """
        while self.consumer_instance is None:
            try:
                ConfluentKafkaMsgQAPI.enable_logging('ConfluentKafkaMsgQAPI:consumer')
                logging.info("Consumer:{}:Trying to connect to broker_hostname={}:{}"
                             .format(self.thread_identifier,
                                     self.broker_hostname,
                                     self.broker_port))
                # Create Consumer instance
                # Hint: try debug='fetch' to generate some log messages
                consumer_conf = {'bootstrap.servers': '{}:{}'.format(self.broker_hostname,
                                                                     self.broker_port),
                                 'group.id': self.topic,
                                 'session.timeout.ms': 6000,
                                 'auto.offset.reset': 'earliest'}

                self.consumer_instance = Consumer(consumer_conf)
            except:
                logging.info("Consumer:{}:Exception in user code:"
                             .format(self.thread_identifier))
                logging.info("-" * 60)
                traceback.print_exc(file=sys.stdout)
                logging.info("-" * 60)
                time.sleep(5)

        logging.info("Consumer:{}:Consumer Successfully "
                     "connected to broker_hostname={}"
                     .format(self.thread_identifier,
                             self.broker_hostname))
        try:
            self.consumer_instance.subscribe([self.topic])
            logging.info("Consumer:{}:Successfully "
                         "subscribed to topic={}"
                         .format(self.thread_identifier,
                                 self.topic))
        except:
            logging.info("Consumer:{}:Exception in user code:"
                         .format(self.thread_identifier))
            logging.info("-" * 60)
            traceback.print_exc(file=sys.stdout)
            logging.info("-" * 60)
            time.sleep(5)

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
        logging.info("Trying to consume messages from {}.".format(consumer_instance.topic))
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                msg = consumer_instance.consumer_instance.consume(timeout=1)
                if msg and not msg.error():
                    msg = msg.value().decode('utf8')
                    logging.info("msg.value()={}".format(msg))
                    consumer_instance.redis_instance.increment_dequeue_count()
                    consumer_instance.subscription_cb(msg)
            except:
                logging.debug("Exception occured when trying to poll a kafka topic.")
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))

    def create_consumer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="consumer_thread",
                                                target=ConfluentKafkaMsgQAPI.run_consumer_thread,
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
        return self.topic

    def disconnect(self):
        if self.consumer_instance:
            self.consumer_instance.close()
        self.consumer_instance = None

    def publish_topic_in_redis_db(self, key_prefix):
        if self.cont_id and len(self.cont_id) >= 12:
            self.redis_instance.set_the_key_in_redis_db(key_prefix, self.topic)
        else:
            key = key_prefix + '_' + self.cont_id[:12]
            self.redis_instance.set_the_key_in_redis_db(key, self.topic)

    def cleanup(self):
        if self.consumer_thread:
            self.consumer_instance.close()
            if getattr(self.consumer_thread, "do_run", True):
                self.consumer_thread.do_run = False
                time.sleep(5)
                logging.info("Trying to join thread {}."
                              .format(self.consumer_thread.getName()))
                self.consumer_thread.join(1.0)
