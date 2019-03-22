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

from subscriber.mqtt_subscriber import Subscriber


class TestMQTTClient(unittest.TestCase):

    def setUp(self):
        os.environ["mqtt_broker_key"] = "172.20.0.2"
        os.environ["mqtt_broker_port_key"] = "1883"
        os.environ["enqueue_topic_key"] = "ThingspaceSDK/12344444444444555/UNITOnBoard"
        os.environ["average_latency_for_n_sec_key"] = "1"
        os.environ["test_duration_in_sec_key"] = "10"
        os.environ["log_level_key"] = "info"
        os.environ["max_consumer_threads_key"] = "1"

    def test_run(self):
        print("Validating **************** Validating MQTT Client Subscriber *****************.")
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
