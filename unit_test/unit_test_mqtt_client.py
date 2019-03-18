import os
import time
import sys
import traceback
import unittest
import subprocess
import threading


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

from mqtt_client import MQTTClient


class TestMQTTClient(unittest.TestCase):

    def setUp(self):
        os.environ["mqtt_broker_key"] = "68.128.155.233"
        os.environ["mqtt_broker_port_key"] = "1889"
        os.environ["message_key"] = "{\
  \"lastUpdated\": \"2018-11-19T18:21:03Z\",\
  \"unitName\": \"VZW_LH_UNIT_01\",\
  \"unitMacId\": \"864508030027459\",\
  \"sensor\": {\
    \"name\": \"cHe_AssetTracker\",\
    \"characteristics\": [\
      {\
        \"characteristicsName\": \"temperature\",\
        \"currentValue\": \"30.2999\",\
        \"readLevel\": \"R\",\
        \"parameterType\": \"Number\",\
        \"measurementUnit\": \"Celcius\"\
      }\
    ]\
  }\
}"
    os.environ["enqueue_topic_key"] = "temp2"
    os.environ["messages_per_second_key"] = "10000"
    os.environ["test_duration_in_sec_key"] = "60"
    os.environ["log_level_key"] = "info"

    def test_run(self):
        print("Validating **************** Validating MQTT Client *****************.")
        worker = MQTTClient()
        MQTTClient.continue_poll = True
        try:
            worker.perform_job()
        except KeyboardInterrupt:
            print("Keyboard interrupt." + sys.exc_info()[0])
            print("Exception in user code:")
            print("-" * 60)
            traceback.print_exc(file=sys.stdout)
            print("-" * 60)
            MQTTClient.continue_poll = False

    def tearDown(self):
        pass


if __name__ == "__main__":
    # To avoid the end of execution traceback adding exit=False
    unittest.main(exit=False)
