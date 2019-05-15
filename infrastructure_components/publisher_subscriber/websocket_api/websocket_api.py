import logging
import os
import sys
import threading
import time
import json
import socket
import subprocess
import struct


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


class WebSocketAPI:
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
            logging.info("WebSocketAPI{}: You need to pick either producer or consumer."
                         .format(thread_identifier))
            pass
        elif is_consumer and not subscription_cb:
            logging.error("WebSocketAPI:{} You need to pass a subscription callback function."
                          .format(thread_identifier))
            pass
        self.is_producer = is_producer
        self.is_consumer = is_consumer
        self.producer_thread = None
        self.consumer_thread = None
        self.is_connected = False
        self.publisher_port_for_sending_message = 0
        self.publisher_port_for_signaling = 0
        self.subscriber_port_for_sending_message = 0
        self.subscriber_port_for_signaling = 0
        self.serversocket = None
        self.clientsocket = None
        self.tcpipsocket = None

        # decode the JSON formatted string.
        dict_of_key_values = json.loads(queue_name)
        if type(dict_of_key_values) != dict:
            logging.error("Unable to decode key value from the queue name.")
            raise KeyboardInterrupt
        logging.info("Successfully decoded the JSON message {}."
                     .format(dict_of_key_values))
        if self.is_producer:
            self.publisher_port_for_sending_message = dict_of_key_values[WebSocketAPI.publisher_port_key]
            self.publisher_port_for_signaling = dict_of_key_values[WebSocketAPI.publisher_signaling_key]
            logging.info("message_port={},signaling_port={}"
                         .format(self.publisher_port_for_sending_message,
                                 self.publisher_port_for_signaling))
        if self.is_consumer:
            self.subscriber_port_for_sending_message = dict_of_key_values[WebSocketAPI.subscriber_port_key]
            self.subscriber_port_for_signaling = dict_of_key_values[WebSocketAPI.subscriber_signaling_key]
            logging.info("message_port={},signaling_port={}"
                         .format(self.subscriber_port_for_sending_message,
                                 self.subscriber_port_for_signaling))
        self.redis_instance = None
        self.client_instance = None
        # self.cont_id = os.popen("cat /etc/hostname").read()
        # self.cont_id = self.cont_id[:-1]
        self.cont_id = "123"
        self.thread_identifier = thread_identifier
        self.subscription_cb = subscription_cb
        self.context = None
        self.syncservice = None
        self.publisher_hostname = "localhost"
        self.publisher = None
        self.subscriber = None
        self.__read_environment_variables()
        if self.is_producer:
            self.create_producer_thread()
        elif self.is_consumer:
            self.create_consumer_thread()

    def __read_environment_variables(self):
        """
        This method is used to read the environment variables defined in the OS.
        :return:
        """
        if self.is_consumer:
            while not self.publisher_hostname:
                time.sleep(2)
                logging.info("WebSocketAPI:{} "
                             "Trying to read the environment variables..."
                             .format(self.thread_identifier))
                self.publisher_hostname = os.getenv("publisher_hostname_key", default=None)

            logging.info("WebSocketAPI:{} publisher_hostname={}"
                         .format(self.thread_identifier,
                                 self.publisher_hostname))

    def connect(self):
        """
        Connect to a broker.
        :return:
        """
        self.redis_instance = RedisInterface(self.thread_identifier)
        if self.is_producer:
            # Socket to talk to clients
            # TODO 1. Create a tcp client socket localhost:port (1234)
            # Create a TCP/IP socket
            # run the jar file by creating a new process. (jar file for publisher)
            list_of_args = ['java',
                            '-jar',
                            'websocket-java-api-client-all.jar',
                            self.publisher_port_for_signaling,
                            'localhost:' + str(self.publisher_port_for_sending_message)]
            os.spawnvpe(os.P_NOWAIT, 'java', list_of_args, os.environ)
            time.sleep(5)
            self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.debug("TCPIP Socket producer side connected at port {}." \
                          .format(self.publisher_port_for_signaling))
            # connect to server on local computer
            self.serversocket.connect(('localhost', int(self.publisher_port_for_signaling)))
            # self.serversocket.setblocking(0)
            # time.sleep(2)
        elif self.is_consumer:
            # First, connect our subscriber socket
            # TODO 1. Create  tcp server socket localhost:port (self.subscriber_port_for_signaling)
            # Create a TCP/IP socket
            # run the jar file for subscriber.
            list_of_args = ['java',
                            '-jar',
                            'Java-WebSocket-1.4.0-all-1.4.1-SNAPSHOT.jar',
                            self.subscriber_port_for_sending_message,
                            'localhost',
                            self.subscriber_port_for_signaling]
            os.spawnvpe(os.P_NOWAIT, 'java', list_of_args, os.environ)

            # Create a TCP/IP socket
            self.tcpipsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Bind the socket to the port
            server_address = ('localhost', int(self.subscriber_port_for_signaling))
            self.tcpipsocket.bind(server_address)
            self.tcpipsocket.listen()

    def subscriber_receive_message(self):
        # msg = self.subscriber.recv()
        # this is the server side for subscription. Therefore, you just need to listen to incoming message.
        conn, addr = self.tcpipsocket.accept()
        msg = conn.recv(4096)
        # msg = msg.decode('utf-8')
        msg = msg.decode(encoding="utf-8", errors="ignore")
        event_message = "\n \n Received message from {}:{},payload={}." \
            .format(self.publisher_hostname,
                    self.subscriber_port_for_sending_message,
                    msg)
        # logging.debug(event_message)
        self.redis_instance.write_an_event_in_redis_db(event_message)
        self.redis_instance.increment_dequeue_count()
        self.subscription_cb(msg)
        conn.close()

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
                                                target=WebSocketAPI.run_consumer_thread,
                                                args=(),
                                                kwargs={'consumer_instance':
                                                            self})
        self.consumer_thread.do_run = True
        self.consumer_thread.name = "consumer"
        self.consumer_thread.start()

    @staticmethod
    def run_producer_thread(*args, **kwargs):
        logging.debug("Starting {}".format(threading.current_thread().getName()))
        producer_instance = None
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'producer_instance':
                producer_instance = value
        t = threading.currentThread()
        producer_instance.connect()
        while getattr(t, "do_run", True):
            time.sleep(1)
        logging.debug("Producer {}: Exiting"
                      .format(threading.current_thread().getName()))

    def create_producer_thread(self):
        self.producer_thread = None
        self.producer_thread = threading.Thread(name="producer_thread",
                                                target=WebSocketAPI.run_producer_thread,
                                                args=(),
                                                kwargs={'producer_instance':
                                                            self})
        self.producer_thread.do_run = True
        self.producer_thread.name = "producer"
        self.producer_thread.start()

    def disconnect(self):
        pass

    def cleanup(self):
        if self.consumer_thread:
            # self.client_instance.disconnect()
            if getattr(self.consumer_thread, "do_run", True):
                if self.is_consumer:
                    self.tcpipsocket.close()
                self.consumer_thread.do_run = False
                time.sleep(5)
                logging.debug("Trying to join thread {}."
                              .format(self.consumer_thread.getName()))
                self.consumer_thread.join(1.0)
            if getattr(self.producer_thread, "do_run", True):
                if self.is_producer:
                    self.serversocket.close()
                    self.serversocket.shutdown(socket.SHUT_RDWR)
                # self.producer_thread.do_run = False
                time.sleep(5)
                # logging.debug("Trying to join thread {}."
                #              .format(self.producer_thread.getName()))
                # self.producer_thread.join(1.0)

    def publish(self, message):
        """
        This method tries to post a message to the pre-defined socket.
        :param message:
        :return status False or True:
        """
        # time.sleep(1)
        # self.serversocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        # connect to server on local computer 
        # self.serversocket.connect(('localhost', int(self.publisher_port_for_signaling)))
        # self.serversocket.connect(('localhost', 6010))
        # self.serversocket.setblocking(False)

        event_message = "\n \n {}: Publishing a message {} to port {}." \
            .format(self.thread_identifier,
                    message,
                    self.publisher_port_for_signaling)
        # logging.debug(event_message)
        self.redis_instance.write_an_event_in_redis_db(event_message)
        # TODO invoke the socket send to send the message via tcp client socket to the producer jar file.
        # logging.debug(message.decode('utf-8'))
        # self.serversocket.send(str(message, 'utf-8'))
        msg_sent_length = 0
        while not msg_sent_length or msg_sent_length < len(message):
            self.serversocket.send(struct.pack("!H", len(message)))
            msg_sent_length = self.serversocket.send(message.encode('utf-8'))
            self.redis_instance.increment_enqueue_count()
            # logging.info("msg_sent_length={},{}".format(msg_sent_length,len(message)))
        # logging.info("Successfully sent a message {} of length {}.".format(message, msg_sent_length))
        # self.serversocket.close()
