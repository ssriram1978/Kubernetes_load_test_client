import logging
import os
import sys
import threading
import time
from collections import deque


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
import asyncio
from nats.aio.client import Client as NATS
import time


class NatsMsgQAPI:
    producer_queue = deque()

    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None,
                 queue_name=None):
        if not is_producer and not is_consumer:
            logging.info("NatsMsgQAPI{}: You need to pick either producer or consumer."
                         .format(thread_identifier))
            pass
        elif is_consumer and not subscription_cb:
            logging.error("NatsMsgQAPI:{} You need to pass a subscription callback function."
                          .format(thread_identifier))
            pass
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.producer_thread = None
        self.consumer_thread = None
        self.is_connected = False
        self.publisher_topic = None
        if self.is_producer:
            self.publisher_topic = queue_name
        self.subscriber_topic = None
        if self.is_consumer:
            self.subscriber_topic = queue_name
        self.redis_instance = None
        self.broker_hostname = None
        self.cont_id = os.popen("cat /etc/hostname").read()
        self.cont_id = self.cont_id[:-1]
        self.thread_identifier = thread_identifier
        self.__read_environment_variables()
        self.subscription_cb = subscription_cb
        if self.is_producer:
            self.create_producer_thread()
        if self.is_consumer:
            self.create_consumer_thread()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        while not self.broker_hostname:
            time.sleep(2)
            logging.info("NatsMsgQAPI:{} "
                         "Trying to read the environment variables..."
                         .format(self.thread_identifier))
            self.broker_hostname = os.getenv("broker_hostname_key", default=None)
            self.broker_port = int(os.getenv("broker_port_key", default="6650"))
        # if self.cont_id and len(self.cont_id) >= 12:
        #    self.topic += '_' + self.cont_id[:12]
        logging.info("NatsMsgQAPI:{} broker_hostname={}"
                     .format(self.thread_identifier,
                             self.broker_hostname))
        logging.info("NatsMsgQAPI:{} publisher_topic={}"
                     .format(self.thread_identifier,
                             self.publisher_topic))
        logging.info("NatsMsgQAPI:{} subscriber_topic={}"
                     .format(self.thread_identifier,
                             self.subscriber_topic))
        logging.info("NatsMsgQAPI:{} broker_port={}"
                     .format(self.thread_identifier,
                             self.broker_port))

    @staticmethod
    async def run_consumer(loop, consumer_instance, t):
        nc = NATS()
        logging.info('Trying to connect to {}:{}'
                     .format(consumer_instance.broker_hostname,
                             consumer_instance.broker_port))
        await nc.connect("{}:{}".format(consumer_instance.broker_hostname,
                                        consumer_instance.broker_port),
                         loop=loop)

        consumer_instance.redis_instance = RedisInterface(threading.current_thread().getName())
        # consumer_instance.publish_topic_in_redis_db(consumer_instance.subscriber_topic)

        async def message_handler(msg):
            message_data = msg.data.decode('utf-8')
            if len(message_data):
                logging.debug("1. Received a message on topic={} subject={} reply={} : data={}"
                             .format(consumer_instance.subscriber_topic,
                                     msg.subject,
                                     msg.reply,
                                     message_data))
                consumer_instance.subscription_cb(message_data)

                event_message = "\n \n Received message from topic: {},payload={}." \
                    .format(consumer_instance.subscriber_topic,
                            message_data)
                logging.debug(event_message)
                consumer_instance.redis_instance.write_an_event_in_redis_db(event_message)
                consumer_instance.redis_instance.increment_dequeue_count()

        if nc.is_connected:
            logging.info("Connected successfully. Trying to subscribe.")
            is_subscribed = False
            while getattr(t, "do_run", True):
                try:
                    if not is_subscribed:
                        await nc.subscribe(subject=consumer_instance.subscriber_topic,
                                           cb=message_handler)
                        is_subscribed = True
                    msg = await nc.request(subject=consumer_instance.subscriber_topic,
                                           payload=b'',
                                           timeout=0.0001)
                    # await nc.subscribe(subject="foo", cb=message_handler)
                except asyncio.TimeoutError:
                    # print("Timed out waiting for response")
                    continue
                except:
                    time.sleep(5)

    @staticmethod
    def run_consumer_thread(*args, **kwargs):
        logging.debug("Starting {}".format(threading.current_thread().getName()))
        consumer_instance = None
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'consumer_instance':
                consumer_instance = value
        t = threading.currentThread()

        loop = asyncio.new_event_loop()
        loop.run_until_complete(NatsMsgQAPI.run_consumer(loop, consumer_instance, t))
        loop.close()
        logging.debug("Consumer {}: Exiting"
                      .format(threading.current_thread().getName()))

    def create_consumer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="consumer_thread",
                                                target=NatsMsgQAPI.run_consumer_thread,
                                                args=(),
                                                kwargs={'consumer_instance':
                                                            self})
        self.consumer_thread.do_run = True
        self.consumer_thread.name = "consumer"
        self.consumer_thread.start()

    @staticmethod
    async def run_producer(loop, instance, t):
        nc = NATS()
        logging.info('Trying to connect to {}:{}'
                     .format(instance.broker_hostname, instance.broker_port))

        await nc.connect("{}:{}".format(instance.broker_hostname,
                                        instance.broker_port),
                         loop=loop)
        instance.redis_instance = RedisInterface(threading.current_thread().getName())
        # instance.publish_topic_in_redis_db(instance.publisher_topic)
        if nc.is_connected:
            logging.info("Connected successfully. Trying to dequeue messages...")
            while getattr(t, "do_run", True):
                message_data = None
                if len(NatsMsgQAPI.producer_queue):
                    message_data = NatsMsgQAPI.producer_queue.popleft()
                if message_data:
                    try:
                        event_message = "\n \n Producing message to topic: {},payload={}." \
                            .format(instance.publisher_topic,
                                    message_data)
                        logging.debug(event_message)
                        instance.redis_instance.write_an_event_in_redis_db(event_message)
                        instance.redis_instance.increment_enqueue_count()
                        await nc.request(subject=instance.publisher_topic,
                                         payload=message_data.encode('utf-8'),
                                         timeout=0.0001)
                    except:
                        logging.debug('caught an exception while publishing a message.')
                        continue

    @staticmethod
    def run_producer_thread(*args, **kwargs):
        logging.debug("Starting {}".format(threading.current_thread().getName()))
        instance = None
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'instance':
                instance = value
        t = threading.currentThread()

        loop = asyncio.new_event_loop()
        loop.run_until_complete(NatsMsgQAPI.run_producer(loop, instance, t))
        loop.close()
        logging.debug("Producer {}: Exiting"
                      .format(threading.current_thread().getName()))

    def create_producer_thread(self):
        self.producer_thread = None
        self.producer_thread = threading.Thread(name="producer_thread",
                                                target=NatsMsgQAPI.run_producer_thread,
                                                args=(),
                                                kwargs={'instance':
                                                            self})
        self.producer_thread.do_run = True
        self.producer_thread.name = "producer"
        self.producer_thread.start()

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
        pass

    def get_topic_name(self):
        if self.is_producer:
            return self.publisher_topic
        elif self.is_consumer:
            return self.subscriber_topic
        else:
            return None

    def cleanup(self):
        self.disconnect()
        if getattr(self.consumer_thread, "do_run", True):
            self.consumer_thread.do_run = False
            time.sleep(5)
            logging.debug("Trying to join thread {}."
                          .format(self.consumer_thread.getName()))
            self.consumer_thread.join(1.0)
        if getattr(self.producer_thread, "do_run", True):
            self.producer_thread.do_run = False
            time.sleep(5)
            logging.debug("Trying to join thread {}."
                          .format(self.producer_thread.getName()))
            self.producer_thread.join(1.0)

    def publish(self, message):
        """
        This method tries to post a message to the pre-defined topic.
        :param message:
        :return status False or True:
        """
        NatsMsgQAPI.producer_queue.append(message)
