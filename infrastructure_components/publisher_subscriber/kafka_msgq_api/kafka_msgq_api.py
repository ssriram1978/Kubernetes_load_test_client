import json
import logging
import os
import sys
import threading
import time
import traceback
from pprint import pformat

import kafka
import confluent_kafka


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


class KafkaMsgQAPI(object):
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
            logging.error("KafkaMsgQAPI: You need to pick either producer or consumer.")
            pass
        elif is_consumer and not subscription_cb:
            logging.error("KafkaMsgQAPI: You need to pass a subscription callback function.")
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
        self.kafka_type = None
        self.thread_identifier = thread_identifier
        self.redis_instance = RedisInterface(self.thread_identifier)
        self.__read_environment_variables()
        if is_producer:
            self.__producer_connect()
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
            logging.info("KafkaMsgQAPI: "
                         "Trying to read the environment variables...")
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="9092"))
            self.kafka_type = os.getenv("kafka_type_key", default="ConfluentKafka")

        logging.info("KafkaMsgQAPI: broker_hostname={}".format(self.broker_hostname))
        logging.info("KafkaMsgQAPI: broker_port={}".format(self.broker_port))
        logging.info("KafkaMsgQAPI: publisher_topic={}".format(self.publisher_topic))
        logging.info("KafkaMsgQAPI: subscriber_topic={}".format(self.subscriber_topic))
        logging.info("KafkaMsgQAPI: kafka_type={}".format(self.kafka_type))

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

    def create_topic(self):
        logging.info("Entering create_topic fn.")
        if not self.is_topic_created:
            topic = None
            if self.is_producer:
                topic = self.publisher_topic
            elif self.is_consumer:
                topic = self.subscriber_topic

            try:
                if self.kafka_type == "ConfluentKafka":
                    kafka_admin_client = confluent_kafka.admin.AdminClient({'bootstrap.servers': '{}:{}'
                                                                           .format(self.broker_hostname,
                                                                                   self.broker_port)})

                    logging.info("Creating topic {}."
                                 .format(topic))
                    ret = kafka_admin_client.create_topics(new_topics=[
                        confluent_kafka.admin.NewTopic(topic=topic,
                                                       timeout_ms=5000,
                                                       num_partitions=self.partitions_per_topic)],
                        operation_timeout=1.0)
                    logging.info("ret = {}".format(ret))
                    if self.producer_instance.list_topics(topic,
                                                          timeout=1.0):
                        logging.info("Found topic name = {} in the zookeeper."
                                     .format(topic))
                else:
                    try:
                        kafka_admin_client = kafka.admin.KafkaAdminClient(
                            bootstrap_servers='{}:{}'.format(self.broker_hostname, self.broker_port))
                    except:
                        logging.info("Caught an exception while trying to invoke admin.KafkaAdminClient.")

                    else:
                        try:
                            logging.info("Creating topic {}."
                                         .format(topic))
                            ret = kafka_admin_client.create_topics(new_topics=[
                                confluent_kafka.admin.NewTopic(name=topic,
                                                               num_partitions=self.partitions_per_topic,
                                                               replication_factor=1)]
                            )
                            logging.info("ret = {}".format(ret))
                        except:
                            logging.info("Caught an exception while trying to create a topic.")
                            # print("-" * 60)
                            # traceback.print_exc(file=sys.stdout)
                            # traceback.print_last()
                            # traceback.print_stack()
                            print("-" * 60)
                        try:
                            logging.info(
                                "Trying to create {} partitions in a topic.".format(self.partitions_per_topic))
                            ret = kafka_admin_client.create_partitions(
                                topic_partitions={
                                    topic: confluent_kafka.admin.NewPartitions(self.partitions_per_topic)})
                            logging.info("ret = {}".format(ret))
                        except:
                            logging.info("Caught an exception while trying to increase "
                                         "the number of partitions a topic.")
                            # print("-" * 60)
                            # traceback.print_exc(file=sys.stdout)
                            # traceback.print_last()
                            # traceback.print_stack()
                            # print("-" * 60)
            except:
                logging.info("Caught an exception.")
                print("-" * 60)
                # traceback.print_exc(file=sys.stdout)
                traceback.print_last()
                # traceback.print_stack()
                print("-" * 60)
            finally:
                self.is_topic_created = True
        else:
            logging.info("self.is_topic_created is already set to True.")

    def __producer_connect(self):
        """
        This method tries to connect to the kafka broker based upon the type of kafka.
        :return:
        """
        while not self.is_producer_connected:
            try:
                # Create Producer instance
                if self.kafka_type == "ConfluentKafka":
                    self.producer_instance = confluent_kafka.Producer({'bootstrap.servers': '{}:{}'
                                                                      .format(self.broker_hostname, self.broker_port)})
                else:
                    self.producer_instance = kafka.KafkaProducer(
                        bootstrap_servers='{}:{}'
                            .format(self.broker_hostname, self.broker_port),
                        max_in_flight_requests_per_connection=1000,
                        batch_size=0,
                        acks=0)

                self.is_producer_connected = True

                # self.publish_topic_in_redis_db(self.publisher_topic)
            except:
                print("Exception in user code:")
                print("-" * 60)
                traceback.print_exc(file=sys.stdout)
                print("-" * 60)
                time.sleep(5)
            else:
                logging.info("KafkaMsgQAPI: Successfully "
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
            logging.info("KafkaMsgQAPI: filename is None or invalid")
            return status

        if not self.is_producer_connected:
            self.__producer_connect()
        if not self.is_topic_created:
            self.create_topic()

        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.

        event_message = "KafkaMsgQAPI: Posting filename={} into kafka broker={}, topic={}" \
            .format(message,
                    self.broker_hostname,
                    self.publisher_topic)
        logging.debug(event_message)

        value = message.encode('utf-8')
        try:
            # Produce line (without newline)
            self.redis_instance.write_an_event_in_redis_db(event_message)
            if self.kafka_type == "ConfluentKafka":
                self.producer_instance.produce(self.publisher_topic, value)
            else:
                self.producer_instance.send(self.publisher_topic, value)
            self.redis_instance.increment_enqueue_count()
            status = True
        except BufferError:
            logging.error('%% Local producer queue is full '
                          '(%d messages awaiting delivery): try again\n' %
                          len(self.producer_instance))
            status = False
        except:
            print("KafkaMsgQAPI: Exception in user code:")
            print("-" * 60)
            traceback.print_exc(file=sys.stdout)
            print("-" * 60)
            status = False
        else:
            event = "KafkaMsgQAPI: Posting message={} into " \
                    "kafka broker={}, topic={}." \
                .format(message,
                        self.broker_hostname,
                        self.publisher_topic)
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
            # self.producer_instance.flush()

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
                if self.kafka_type == "ConfluentKafka":
                    self.consumer_instance = confluent_kafka.Consumer({
                        'bootstrap.servers': '{}:{}'.format(self.broker_hostname, self.broker_port),
                        'group.id': 'kafka-consumer',
                        'auto.offset.reset': 'earliest'
                    })
                else:
                    self.consumer_instance = kafka.KafkaConsumer(
                        bootstrap_servers='{}:{}'.format(self.broker_hostname, self.broker_port),
                        max_in_flight_requests_per_connection=1000,
                        max_poll_records=1000,
                        group_id="kafka-consumer")

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

        try:
            self.consumer_instance.subscribe([self.subscriber_topic])
            logging.info("Consumer:{}:Successfully "
                         "subscribed to topic={}"
                         .format(self.thread_identifier,
                                 self.subscriber_topic))
            # self.publish_topic_in_redis_db(self.subscriber_topic)
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
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            try:
                if consumer_instance.kafka_type == "ConfluentKafka":
                    msg = consumer_instance.consumer_instance.poll(1.0)
                    if msg is None:
                        logging.info("No messages.")
                        continue
                    if msg.error():
                        logging.info("Consumer error: {}".format(msg.error()))
                        continue
                    if msg:
                        logging.info("msg={}.".format(msg.value.decode('utf-8')))
                        KafkaMsgQAPI.process_subscriber_message(consumer_instance,
                                                                msg.value.decode('utf-8'))
                else:
                    msgs = consumer_instance.consumer_instance.poll(timeout_ms=0,
                                                                    max_records=1000
                                                                    )
                    for msg in msgs.values():
                        msg = msg[0].value.decode('utf-8')
                        if msg:
                            KafkaMsgQAPI.process_subscriber_message(consumer_instance, msg)
            except:
                logging.debug("Exception occured when trying to poll a kafka topic.")
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))

    def create_consumer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="consumer_thread",
                                                target=KafkaMsgQAPI.run_consumer_thread,
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
