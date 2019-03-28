import os
import time
import sys
import traceback
import unittest


def import_all_packages():
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


import_all_packages()

from subscriber.subscriber import Subscriber


class TestSubscriberClient(unittest.TestCase):

    def setUp(self):
        os.environ["broker_hostname_key"] = "68.128.155.233"
        os.environ["broker_port_key"] = "1888"
        os.environ["topic_key"] = "ThingspaceSDK/12344444444444555/UNITOnBoard"
        os.environ["average_latency_for_n_sec_key"] = "1"
        os.environ["test_duration_in_sec_key"] = "100"
        os.environ["log_level_key"] = "info"
        os.environ["max_consumer_threads_key"] = "1"
        os.environ["redis_server_hostname_key"] = "68.128.155.233"
        os.environ["redis_server_port_key"] = "6379"
        os.environ["redis_log_keyname_key"] = "consume_load_test"
        os.environ["total_job_enqueued_count_redis_name_key"] = "total_produced_count"
        os.environ["total_job_dequeued_count_redis_name_key"] = "total_consumed_count"
        os.environ["type_of_messaging_queue_key"] = "RabbitMQ"

    def test_run(self):
        print("Validating **************** Validating Subscriber Client *****************.")
        worker = Subscriber()
        try:
            worker.perform_job()
        except KeyboardInterrupt:
            print("Exception in user code:")
            print("-" * 60)
            traceback.print_exc(file=sys.stdout)
            print("-" * 60)

    def tearDown(self):
        pass


if __name__ == "__main__":
    # To avoid the end of execution traceback adding exit=False
    unittest.main(exit=False)