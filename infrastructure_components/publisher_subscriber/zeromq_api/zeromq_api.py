import logging
import os
import sys
import threading
import time
import json

import zmq


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


class ZeroMsgQAPI:
    publisher_port_key = 'PUB'
    subscriber_port_key = 'SUB'
    publisher_signaling_key = 'REP'
    subscriber_signaling_key = 'REQ'

    def __init__(self,
                 is_producer=False,
                 is_consumer=False,
                 thread_identifier=None,
                 subscription_cb=None,
                 queue_name=None):
        if not is_producer and not is_consumer:
            logging.info("ZeroMsgQAPI{}: You need to pick either producer or consumer."
                         .format(thread_identifier))
            pass
        elif is_consumer and not subscription_cb:
            logging.error("ZeroMsgQAPI:{} You need to pass a subscription callback function."
                          .format(thread_identifier))
            pass
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.consumer_thread = None
        self.is_connected = False
        self.publisher_port_for_sending_message = 0
        self.publisher_port_for_signaling = 0
        self.subscriber_port_for_sending_message = 0
        self.subscriber_port_for_signaling = 0

        # decode the JSON formatted string.
        dict_of_key_values = json.loads(queue_name)
        if type(dict_of_key_values) != dict:
            logging.error("Unable to decode key value from the queue name.")
            raise KeyboardInterrupt
        logging.info("Successfully decoded the JSON message {}."
                     .format(dict_of_key_values))
        if self.is_producer:
            self.publisher_port_for_sending_message = dict_of_key_values[ZeroMsgQAPI.publisher_port_key]
            self.publisher_port_for_signaling = dict_of_key_values[ZeroMsgQAPI.publisher_signaling_key]
            logging.info("message_port={},signaling_port={}"
                         .format(self.publisher_port_for_sending_message,
                                 self.publisher_port_for_signaling))
        if self.is_consumer:
            self.subscriber_port_for_sending_message = dict_of_key_values[ZeroMsgQAPI.subscriber_port_key]
            self.subscriber_port_for_signaling = dict_of_key_values[ZeroMsgQAPI.subscriber_signaling_key]
            logging.info("message_port={},signaling_port={}"
                         .format(self.subscriber_port_for_sending_message,
                                 self.subscriber_port_for_signaling))
        self.redis_instance = None
        self.client_instance = None
        self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.thread_identifier = thread_identifier
        self.subscription_cb = subscription_cb
        self.context = None
        self.syncservice = None
        self.publisher_hostname = None
        self.__read_environment_variables()
        if self.is_producer:
            self.publisher = None
            self.connect()
        elif self.is_consumer:
            self.subscriber = None
            self.create_consumer_thread()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        if self.is_consumer:
            while not self.publisher_hostname:
                time.sleep(2)
                logging.info("ZeroMsgQAPI:{} "
                             "Trying to read the environment variables..."
                             .format(self.thread_identifier))
                self.publisher_hostname = os.getenv("publisher_hostname_key", default=None)

            logging.info("ZeroMsgQAPI:{} publisher_hostname={}"
                         .format(self.thread_identifier,
                                 self.publisher_hostname))

    def connect(self):
        """
        Connect to a broker.
        :return:
        """
        self.redis_instance = RedisInterface(self.thread_identifier)
        self.context = zmq.Context()
        if self.is_producer:
            # Socket to talk to clients
            self.publisher = self.context.socket(zmq.PUB)
            # set SNDHWM, so we don't drop messages for slow subscribers
            self.publisher.sndhwm = 1100000
            self.publisher.bind('tcp://*:{}'.format(self.publisher_port_for_sending_message))
            # Socket to receive signals
            self.syncservice = self.context.socket(zmq.REP)
            self.syncservice.bind('tcp://*:{}'.format(self.publisher_port_for_signaling))
            # wait for synchronization request
            logging.info("Waiting for subscribers to connect to this server at signaling port {}."
                         .format(self.publisher_port_for_signaling))
            msg = self.syncservice.recv()
            logging.info("Received a request from a client {} to connect to this server."
                         .format(msg))
            # send synchronization reply
            resp = 'Accepted your request from server message_port={},signaling_port={}' \
                .format(self.publisher_port_for_sending_message,
                        self.publisher_port_for_signaling)
            self.syncservice.send(resp.encode('utf-8'))
            logging.info("Sent a response back to the client {}."
                         .format(msg))
        elif self.is_consumer:
            # First, connect our subscriber socket
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect('tcp://{}:{}'
                                    .format(self.publisher_hostname,
                                            self.subscriber_port_for_sending_message))
            self.subscriber.setsockopt(zmq.SUBSCRIBE, b'')
            # Second, synchronize with publisher
            self.syncservice = self.context.socket(zmq.REQ)
            logging.info("Trying to connect to publisher {}:{}."
                         .format(self.publisher_hostname,
                                 self.subscriber_port_for_signaling))
            self.syncservice.connect('tcp://{}:{}'
                                     .format(self.publisher_hostname,
                                             self.subscriber_port_for_signaling))
            msg = 'client message_port={}, signaling_port={} requesting subscription.' \
                .format(self.subscriber_port_for_sending_message,
                        self.subscriber_port_for_signaling)
            logging.info("Sending a synchronization request {} to server."
                         .format(msg))
            # send a synchronization request
            self.syncservice.send(msg.encode('utf-8'))

            # wait for synchronization reply
            msg = self.syncservice.recv()
            logging.info("Received a synchronization response {} from the server."
                         .format(msg))

    def subscriber_receive_message(self):
        msg = self.subscriber.recv()
        msg = msg.decode('utf-8')
        event_message = "\n \n Received message from {}:{},payload={}." \
            .format(self.publisher_hostname,
                    self.publisher_port_for_sending_message,
                    msg)
        logging.debug(event_message)
        self.redis_instance.write_an_event_in_redis_db(event_message)
        self.redis_instance.increment_dequeue_count()
        self.subscription_cb(msg)

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
            consumer_instance.subscriber_receive_message()
        logging.debug("Consumer {}: Exiting"
                      .format(threading.current_thread().getName()))

    def create_consumer_thread(self):
        self.consumer_thread = None
        self.consumer_thread = threading.Thread(name="consumer_thread",
                                                target=ZeroMsgQAPI.run_consumer_thread,
                                                args=(),
                                                kwargs={'consumer_instance':
                                                            self})
        self.consumer_thread.do_run = True
        self.consumer_thread.name = "consumer"
        self.consumer_thread.start()

    def disconnect(self):
        pass

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
        This method tries to post a message to the pre-defined socket.
        :param message:
        :return status False or True:
        """

        event_message = "\n \n {}: Publishing a message {} to port {}." \
            .format(self.thread_identifier,
                    message,
                    self.publisher_port_for_sending_message)
        logging.debug(event_message)
        self.redis_instance.write_an_event_in_redis_db(event_message)
        self.publisher.send(message.encode('utf-8'))
        self.redis_instance.increment_enqueue_count()
