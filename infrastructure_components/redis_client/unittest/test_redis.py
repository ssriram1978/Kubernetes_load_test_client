import os
import sys
import subprocess
import unittest
import logging

def import_all_paths():
    realpath = os.path.realpath(__file__)
    # print("os.path.realpath({})={}".format(__file__,realpath))
    dirname = os.path.dirname(realpath)
    # print("os.path.dirname({})={}".format(realpath,dirname))
    dirname_list = dirname.split('/')
    #print(dirname_list)
    for index in range(len(dirname_list)):
        module_path = '/'.join(dirname_list[:index])
        #print("module_path={}".format(module_path))
        try:
            sys.path.append(module_path)
        except:
            #print("Invalid module path {}".format(module_path))
            pass



import_all_paths()

from infrastructure_components.redis_client.redis_client import RedisClient
from infrastructure_components.redis_client.redis_interface import RedisInterface


class TestRedisInterface(unittest.TestCase):
    def setUp(self):
        os.environ["redis_log_keyname_key"] = "load_test"
        os.environ["total_job_enqueued_count_redis_name_key"] = "publish"
        os.environ["total_job_dequeued_count_redis_name_key"] = "subscribe"
        self.dirname = os.path.dirname(os.path.realpath(__file__))
        self.create_test_docker_container()
        self.redisInterface = RedisInterface()

    def test_redis_interface(self):
        self.assertEqual(self.redisInterface.get_current_enqueue_count(), -1)
        self.assertEqual(self.redisInterface.get_current_dequeue_count(), -1)
        self.redisInterface.increment_enqueue_count()
        self.assertEqual(self.redisInterface.get_current_enqueue_count().decode('utf8'), '1')
        self.redisInterface.increment_dequeue_count()
        self.assertEqual(self.redisInterface.get_current_enqueue_count().decode('utf8'), '1')

    def create_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_redis.yml".format(self.dirname),
                                           "up",
                                           "-d"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)
        # time.sleep(120)

    def delete_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_redis.yml".format(self.dirname),
                                           "down"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)

    def tearDown(self):
        self.delete_test_docker_container()


class TestRedisClient(unittest.TestCase):
    def setUp(self):
        os.environ["redis_server_hostname_key"] = "localhost"
        os.environ["redis_log_keyname_key"] = "mqtt_load_test"
        os.environ["redis_server_port_key"] = "6379"
        self.dirname = os.path.dirname(os.path.realpath(__file__))
        self.create_test_docker_container()
        self.redisClient = RedisClient()

    def create_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_redis.yml".format(self.dirname),
                                           "up",
                                           "-d"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)
        # time.sleep(120)

    def delete_test_docker_container(self):
        completedProcess = subprocess.run(["docker-compose",
                                           "-f",
                                           "{}/docker-compose_redis.yml".format(self.dirname),
                                           "down"],
                                          stdout=subprocess.PIPE)
        self.assertIsNotNone(completedProcess)
        self.assertIsNotNone(completedProcess.stdout)

    def test_key_in_redis(self):
        redisClient_inst1 = RedisClient()
        self.assertTrue(redisClient_inst1.set_the_key_in_redis_db("abcxyz"))
        self.assertTrue(redisClient_inst1.check_if_the_key_exists_in_redis_db("abcxyz"))

    def test_delete_key_in_redis(self):
        redisClient_inst1 = RedisClient()
        self.assertTrue(redisClient_inst1.set_the_key_in_redis_db("abcxyz1"))
        self.assertTrue(redisClient_inst1.delete_key_from_redis_db("abcxyz1"))
        self.assertFalse(redisClient_inst1.check_if_the_key_exists_in_redis_db("abcxyz1"))

    def test_singleton(self):
        redisClient_inst1 = RedisClient()
        redisClient_inst2 = RedisClient()
        self.assertEqual(redisClient_inst1, redisClient_inst2)
        self.assertEqual(self.redisClient, redisClient_inst1)

    def test_redis_connection(self):
        redisClient_inst1 = RedisClient()
        self.assertIsNotNone(redisClient_inst1.redis_instance)

    def test_write_event(self):
        redisClient_inst1 = RedisClient()
        redisClient_inst1.cont_id = "12345"
        self.assertTrue(redisClient_inst1.write_an_event_on_redis_db("Hello world"))
        self.assertTrue(redisClient_inst1.write_an_event_on_redis_db("Hello world2"))
        self.assertTrue(redisClient_inst1.check_if_the_key_exists_in_redis_db(redisClient_inst1.cont_id))

    def test_incr_key(self):
        redisClient_inst1 = RedisClient()
        self.assertTrue(redisClient_inst1.increment_key_in_redis_db("incr_key"))
        self.assertEqual(redisClient_inst1.read_key_value_from_redis_db("incr_key"), b'1')
        self.assertTrue(redisClient_inst1.increment_key_in_redis_db("incr_key"))
        self.assertEqual(redisClient_inst1.read_key_value_from_redis_db("incr_key"), b'2')
        self.assertTrue(redisClient_inst1.increment_key_in_redis_db("incr_key"))
        self.assertEqual(redisClient_inst1.read_key_value_from_redis_db("incr_key"), b'3')

    def test_find_keys_matching_pattern(self):
        redisClient_inst1 = RedisClient()
        for index in range(10):
            self.assertTrue(redisClient_inst1.set_the_key_in_redis_db("key{}".format(index)))
        keys = redisClient_inst1.find_keys_matching_a_pattern("key")
        logging.debug("keys = {}".format(keys))
        self.assertNotEqual(len(keys), 0)
        for key in keys:
            self.assertTrue(key.decode('utf-8').find('key') >= 0)

    def tearDown(self):
        self.redisClient.delete_key_from_redis_db("abcxyz")
        self.redisClient.delete_key_from_redis_db("incr_key")
        self.redisClient.delete_key_from_redis_db(self.redisClient.cont_id)
        self.delete_test_docker_container()


if __name__ == "__main__":
    # To avoid the end of execution traceback adding exit=False
    unittest.main(exit=False)
