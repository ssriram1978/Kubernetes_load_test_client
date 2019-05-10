import logging
import os
import subprocess
import sys
import threading
import time
import unittest
import json

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

from websocket_api.websocket_api import WebSocketAPI

logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',
                    level=logging.DEBUG,
                    datefmt='%m/%d/%Y %I:%M:%S %p')


class TestWebSocket(unittest.TestCase):
    redis_instance = None

    def setUp(self):
        self.dirname = os.path.dirname(os.path.realpath(__file__))
        self.max_consumer_threads = 1
        self.producer_instance = None
        self.consumer_threads = None

    @staticmethod
    def subscription_cb_fn(msg):
        """
        This callback fn gets invoked the client sees a message on the 'topic' that it subscribed.
        :param userdata:
        :param msg:
        :return:
        """
        logging.info("Consumer {}: Dequeued Message = {}"
                      .format(threading.current_thread().getName(),
                              msg))

    @staticmethod
    def run_consumer_instance(*args, **kwargs):
        subscription_cb_function = None
        logging.debug("Starting {}".format(threading.current_thread().getName()))
        for name, value in kwargs.items():
            logging.debug("name={},value={}".format(name, value))
            if name == 'subscription_cb':
                subscription_cb_function = value

        t = threading.currentThread()
        dict_of_values = {}
        dict_of_values["SUB"] = "5000"
        dict_of_values["REQ"]= "5010"
        consumer_instance = WebSocketAPI(is_consumer=True,
                                                   thread_identifier="Consumer",
                                                   queue_name=json.dumps(dict_of_values),
                                                   subscription_cb=subscription_cb_function)
        while getattr(t, "do_run", True):
            time.sleep(1)
        logging.debug("************ Test ended. Cleaning up...******************************")
        consumer_instance.cleanup()
        logging.debug("Consumer {}: Exiting"
                      .format(threading.current_thread().getName()))

    def create_consumer_threads(self, msgq_type):
        self.consumer_threads = [0] * self.max_consumer_threads
        for index in range(self.max_consumer_threads):
            self.consumer_threads[index] = threading.Thread(name="{}{}".format("thread", index),
                                                            target=TestWebSocket.run_consumer_instance,
                                                            args=(),
                                                            kwargs={
                                                                'subscription_cb': TestWebSocket.subscription_cb_fn}
                                                            )
            self.consumer_threads[index].do_run = True
            self.consumer_threads[index].name = "{}_{}".format("consumer", index)
            self.consumer_threads[index].start()

    def create_consumers(self, msgq_type):
        self.create_consumer_threads(msgq_type)
        logging.debug("Validating consumer threads to be not null.")
        for index in range(self.max_consumer_threads):
            self.assertIsNotNone(self.consumer_threads[index])

    def create_producer_and_produce_jobs(self, msgq_type):

        dict_of_values = {}
        dict_of_values["PUB"] = "5000"
        dict_of_values["REP"]= "6010"
        self.producer_instance = WebSocketAPI(is_producer=True,
                                                        thread_identifier="Producer",
                                              queue_name=json.dumps(dict_of_values))
        time.sleep(5)
        logging.debug("Posting messages.")
        self.assertTrue(self.post_messages())

    def start_produce_consume_activity(self, msg_q_type):
        logging.debug("Creating consumer threads to consume jobs.")
        self.create_consumers(msg_q_type)
        time.sleep(30)
        logging.debug("Creating producer instance and producing jobs.")
        self.create_producer_and_produce_jobs(msg_q_type)
        time.sleep(10)

    def test_run(self):
        logging.debug("Validating **************** WEBSOCKET *****************.")
        self.start_produce_consume_activity("None")

    def post_messages(self):
        messages = [str(x) for x in range(1, 10)]
        for message in messages:
            self.producer_instance.publish(message)
        self.producer_instance.cleanup()
        return True


    def cleanup_test_environment(self):
        for index in range(self.max_consumer_threads):
            self.consumer_threads[index].do_run = False
        time.sleep(5)
        #self.delete_test_docker_container()
        for index in range(self.max_consumer_threads):
            logging.debug("Trying to join thread {}."
                          .format(self.consumer_threads[index].getName()))
            self.consumer_threads[index].join(1.0)
            time.sleep(5)
            if self.consumer_threads[index].is_alive():
                raise KeyboardInterrupt

    def tearDown(self):
        self.cleanup_test_environment()
        time.sleep(5)


if __name__ == "__main__":
    # To avoid the end of execution traceback adding exit=False
    unittest.main(exit=True)
