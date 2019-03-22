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

from publisher.publisher import Publisher


class TestClient(unittest.TestCase):

    def setUp(self):
        os.environ["broker_key"] = "172.20.0.2"
        os.environ["broker_port_key"] = "1883"
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

    os.environ["enqueue_topic_key"] = "ThingspaceSDK/12344444444444555/UNITOnBoard"
    os.environ["messages_per_second_key"] = "100"
    os.environ["test_duration_in_sec_key"] = "100"
    os.environ["log_level_key"] = "info"
    os.environ["redis_server_hostname_key"] = "redis"
    os.environ["redis_server_port_key"] = "6379"
    os.environ["broker_type_key"] = "mqtt"

    def test_run(self):
        print("Validating **************** Validating Client Publisher *****************.")
        worker = Publisher()
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
