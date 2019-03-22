import os
import time
import sys
import traceback
import logging
import unittest
import subprocess
import threading


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

from publisher_subscriber.producer_consumer import ProducerConsumerAPI
from redis_client.redis_interface import RedisInterface


class TestProducerConsumer(unittest.TestCase):
    def setUp(self):
        os.environ["broker_name_key"] = "localhost:9094"
        os.environ["topic_key"] = "video-file-name"
        os.environ["redis_log_keyname_key"] = "producer_consumer"
        os.environ["total_job_enqueued_count_redis_name_key"] = "enqueue"
        os.environ["total_job_dequeued_count_redis_name_key"] = "dequeue"
        os.environ["redis_server_hostname_key"] = "localhost"
        os.environ["redis_server_port_key"] = "6379"
        self.dirname = os.path.dirname(os.path.realpath(__file__))
        self.max_consumer_threads = 10
        self.create_test_docker_container()
        self.producer_instance = None
        self.consumer_threads = None

    @staticmethod
    def run_consumer_instance(*args, **kwargs):
        perform_subscription = False
        msgq_type = False
        logging.info("Starting {}".format(threading.current_thread().getName()))
        for name, value in kwargs.items():
            logging.info("name={},value={}".format(name, value))
            if name == 'msgq_type':
                msgq_type = value
            elif name == 'perform_subscription':
                perform_subscription = value

        t = threading.currentThread()

        consumer_instance = ProducerConsumerAPI(is_consumer=True,
                                                thread_identifier=threading.current_thread().getName(),
                                                perform_subscription=perform_subscription,
                                                type_of_messaging_queue=msgq_type)
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            message = consumer_instance.subscribe()
            if message:
                logging.info("Consumer {}: Dequeued Message = {}"
                             .format(threading.current_thread().getName(),
                                     message))
                time.sleep(5)
        consumer_instance.cleanup()
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))

    def create_consumer_threads(self, msgq_type, perform_subscription):
        self.consumer_threads = [0] * self.max_consumer_threads
        for index in range(self.max_consumer_threads):
            self.consumer_threads[index] = threading.Thread(name="{}{}".format("thread", index),
                                                            target=TestProducerConsumer.run_consumer_instance,
                                                            args=(),
                                                            kwargs={'msgq_type': msgq_type,
                                                                    'perform_subscription': perform_subscription}
                                                            )
            self.consumer_threads[index].do_run = True
            self.consumer_threads[index].name = "{}_{}".format("consumer", index)
            self.consumer_threads[index].start()

    def create_consumers(self, msgq_type, perform_subscription):
        self.create_consumer_threads(msgq_type, perform_subscription)
        logging.info("Validating consumer threads to be not null.")
        for index in range(self.max_consumer_threads):
            self.assertIsNotNone(self.consumer_threads[index])

    def create_producer_and_produce_jobs(self, msgq_type):
        self.producer_instance = ProducerConsumerAPI(is_producer=True,
                                                     thread_identifier="Producer",
                                                     type_of_messaging_queue=msgq_type)
        logging.info("Posting messages.")
        self.assertTrue(self.post_messages())

    def perform_enqueue_dequeue(self, msgq_type, perform_subscription=False):
        logging.info("Creating consumer threads to consume jobs.")
        self.create_consumers(msgq_type, perform_subscription)
        time.sleep(10)
        logging.info("Creating producer instance and producing jobs.")
        self.create_producer_and_produce_jobs(msgq_type)
        time.sleep(120)
        logging.info("Validating if the consumer successfully dequeued messages.")
        redis_instance = RedisInterface(threading.current_thread().getName())
        self.assertEqual(redis_instance.get_current_enqueue_count(),
                         redis_instance.get_current_dequeue_count())
        logging.info("enqueue_count={},dequeue_count={}"
                     .format(redis_instance.get_current_enqueue_count(),
                             redis_instance.get_current_dequeue_count()))

    def test_run(self):
        # logging.info("Validating **************** KAFKA MSGQ *****************.")
        # self.perform_enqueue_dequeue(ProduceConsumeAPI.kafkaMsgQType)
        # self.cleanup_test_environment()
        # logging.info("Validating **************** KAFKA MSGQ + SUBSCRIPTION *****************.")
        self.perform_enqueue_dequeue(ProducerConsumerAPI.kafkaMsgQType,
                                     perform_subscription=True)
        logging.info("Validating **************** RABBIT MSGQ  *****************.")
        # self.perform_enqueue_dequeue(ProduceConsumeAPI.rabbitMsgQType)
        # self.cleanup_test_environment()

    def post_messages(self):
        messages = [str(x) for x in range(100)]
        for message in messages:
            self.producer_instance.publish(message)
        self.producer_instance.cleanup()
        return True

    def create_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_wurstmeister_kafka.yml".format(self.dirname),
                                           "up",
                                           "-d"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)
        # time.sleep(120)

    def delete_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_wurstmeister_kafka.yml".format(self.dirname),
                                           "down"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)

    def cleanup_test_environment(self):
        for index in range(self.max_consumer_threads):
            self.consumer_threads[index].do_run = False
        time.sleep(5)
        self.delete_test_docker_container()
        for index in range(self.max_consumer_threads):
            logging.info("Trying to join thread {}."
                         .format(self.consumer_threads[index].getName()))
            self.consumer_threads[index].join(1.0)
            time.sleep(1)
            if self.consumer_threads[index].is_alive():
                try:
                    logging.info("Trying to __stop thread {}."
                                 .format(self.consumer_threads[index].getName()))
                    self.consumer_threads[index].__stop()

                except:
                    logging.info("Caught an exception while stopping thread {}"
                                 .format(self.consumer_threads[index].getName()))

    def tearDown(self):
        self.cleanup_test_environment()
        time.sleep(5)


class TestConfluentProducerConsumer(unittest.TestCase):
    def setUp(self):
        os.environ["broker_name_key"] = "localhost:9092"
        os.environ["topic_key"] = "video-file-name"
        os.environ["redis_log_keyname_key"] = "producer_consumer"
        os.environ["total_job_enqueued_count_redis_name_key"] = "enqueue"
        os.environ["total_job_dequeued_count_redis_name_key"] = "dequeue"
        os.environ["redis_server_hostname_key"] = "localhost"
        os.environ["redis_server_port_key"] = "6379"
        self.dirname = os.path.dirname(os.path.realpath(__file__))
        self.max_consumer_threads = 10
        self.create_test_docker_container()
        self.producer_instance = None
        self.consumer_threads = None

    @staticmethod
    def run_consumer_instance(*args, **kwargs):
        perform_subscription = False
        msgq_type = False
        logging.info("Starting {}".format(threading.current_thread().getName()))
        for name, value in kwargs.items():
            logging.info("name={},value={}".format(name, value))
            if name == 'msgq_type':
                msgq_type = value
            elif name == 'perform_subscription':
                perform_subscription = value

        t = threading.currentThread()

        consumer_instance = ProducerConsumerAPI(is_consumer=True,
                                                thread_identifier=threading.current_thread().getName(),
                                                perform_subscription=perform_subscription,
                                                type_of_messaging_queue=msgq_type)
        while getattr(t, "do_run", True):
            t = threading.currentThread()
            message = consumer_instance.subscribe()
            if message:
                logging.info("Consumer {}: Dequeued Message = {}"
                             .format(threading.current_thread().getName(),
                                     message))
                time.sleep(5)
        consumer_instance.cleanup()
        logging.info("Consumer {}: Exiting"
                     .format(threading.current_thread().getName()))

    def create_consumer_threads(self, msgq_type, perform_subscription):
        self.consumer_threads = [0] * self.max_consumer_threads
        for index in range(self.max_consumer_threads):
            self.consumer_threads[index] = threading.Thread(name="{}{}".format("thread", index),
                                                            target=TestProducerConsumer.run_consumer_instance,
                                                            args=(),
                                                            kwargs={'msgq_type': msgq_type,
                                                                    'perform_subscription': perform_subscription}
                                                            )
            self.consumer_threads[index].do_run = True
            self.consumer_threads[index].name = "{}_{}".format("consumer", index)
            self.consumer_threads[index].start()

    def create_consumers(self, msgq_type, perform_subscription):
        self.create_consumer_threads(msgq_type, perform_subscription)
        logging.info("Validating consumer threads to be not null.")
        for index in range(self.max_consumer_threads):
            self.assertIsNotNone(self.consumer_threads[index])

    def create_producer_and_produce_jobs(self, msgq_type):
        self.producer_instance = ProducerConsumerAPI(is_producer=True,
                                                     thread_identifier="Producer",
                                                     type_of_messaging_queue=msgq_type)
        logging.info("Posting messages.")
        self.assertTrue(self.post_messages())

    def perform_enqueue_dequeue(self, msgq_type, perform_subscription=False):
        logging.info("Creating producer instance and producing jobs.")
        self.create_producer_and_produce_jobs(msgq_type)
        time.sleep(10)
        logging.info("Creating consumer threads to consume jobs.")
        self.create_consumers(msgq_type, perform_subscription)
        time.sleep(120)
        logging.info("Validating if the consumer successfully dequeued messages.")
        redis_instance = RedisInterface(threading.current_thread().getName())
        self.assertEqual(redis_instance.get_current_enqueue_count(),
                         redis_instance.get_current_dequeue_count())
        logging.info("enqueue_count={},dequeue_count={}"
                     .format(redis_instance.get_current_enqueue_count(),
                             redis_instance.get_current_dequeue_count()))

    def test_run(self):
        self.perform_enqueue_dequeue(ProducerConsumerAPI.confluentKafkaMsgQType,
                                     perform_subscription=True)

    def post_messages(self):
        messages = [str(x) for x in range(100)]
        for message in messages:
            self.producer_instance.publish(message)
        self.producer_instance.cleanup()
        return True

    def create_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_confluent_kafka.yml".format(self.dirname),
                                           "up",
                                           "-d"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)
        # time.sleep(120)

    def delete_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_confluent_kafka.yml".format(self.dirname),
                                           "down"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)

    def cleanup_test_environment(self):
        for index in range(self.max_consumer_threads):
            self.consumer_threads[index].do_run = False
        time.sleep(5)
        self.delete_test_docker_container()
        for index in range(self.max_consumer_threads):
            logging.info("Trying to join thread {}."
                         .format(self.consumer_threads[index].getName()))
            self.consumer_threads[index].join(1.0)
            time.sleep(1)
            if self.consumer_threads[index].is_alive():
                try:
                    logging.info("Trying to __stop thread {}."
                                 .format(self.consumer_threads[index].getName()))
                    self.consumer_threads[index].__stop()

                except:
                    logging.info("Caught an exception while stopping thread {}"
                                 .format(self.consumer_threads[index].getName()))

    def tearDown(self):
        self.cleanup_test_environment()
        time.sleep(5)


if __name__ == "__main__":
    # To avoid the end of execution traceback adding exit=False
    unittest.main(exit=False)
