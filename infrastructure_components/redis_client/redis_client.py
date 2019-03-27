import logging
import os
import sys
import time
from datetime import datetime

import redis


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


class RedisClient(object):
    __instance = None

    def __new__(cls):
        if RedisClient.__instance is None:
            RedisClient.__instance = object.__new__(cls)
        return RedisClient.__instance

    def __init__(self):
        logging.info("Instantiating RedisClient.")
        self.redis_instance = None
        self.redis_server_hostname = None
        self.redis_server_port = 0
        self.load_environment_variables()
        self.connect_to_redis_server()
        self.hostname = os.popen("cat /etc/hostname").read()
        self.cont_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.cont_id = self.cont_id[:12]

    def load_environment_variables(self):
        while not self.redis_server_hostname or \
                self.redis_server_port == 0:
            time.sleep(2)
            logging.info("Redis Client: Trying to read "
                         "the environment variables...")
            self.redis_server_hostname = os.getenv("redis_server_hostname_key",
                                                   default=None)
            self.redis_server_port = int(os.getenv("redis_server_port_key",
                                                   default=0))

        logging.info("redis_server_hostname={}"
                     .format(self.redis_server_hostname))
        logging.info("redis_server_port={}"
                     .format(self.redis_server_port))

    def connect_to_redis_server(self):
        while self.redis_instance is None:
            self.redis_instance = redis.StrictRedis(host=self.redis_server_hostname,
                                                    port=self.redis_server_port,
                                                    db=0)
        logging.info("Successfully connected "
                     "to redisClient server {},port {}"
                     .format(self.redis_server_hostname,
                             self.redis_server_port))

    def write_an_event_on_redis_db(self, event, key=None):
        return_value = False
        key_name = None
        if self.redis_instance:
            current_time = datetime.now()
            event_string = "\n Time={},Hostname={},containerID={},event={}" \
                .format(str(current_time),
                        self.hostname,
                        self.cont_id[:12],
                        event)
            if key:
                key_name = key
            else:
                key_name = self.cont_id
            try:
                if self.redis_instance.exists(key_name):
                    self.redis_instance.append(key_name, event_string)
                    logging.debug("Appending "
                                  "{} to {}".format(event_string, key_name))
                    return_value = True
                else:
                    self.redis_instance.set(key_name, event_string)
                    logging.debug("Writing "
                                  "{} to {}".format(event_string, key_name))
                    return_value = True
            except redis.exceptions.ConnectionError:
                logging.error("Unable to connect to Redis server.")
            except BaseException:
                logging.error("Base Except: Unable to connect to Redis server.")
        return return_value

    def check_if_the_key_exists_in_redis_db(self, key):
        return_value = False
        if self.redis_instance:
            try:
                if self.redis_instance.exists(key):
                    return_value = True
            except redis.exceptions.ConnectionError:
                logging.error("Unable to connect to Redis server.")
            except BaseException:
                logging.error("Base Except: Unable to connect to Redis server.")
        return return_value

    def set_the_key_in_redis_db(self, key, value=1):
        return_value = False
        if self.redis_instance:
            try:
                self.redis_instance.set(key, value)
                return_value = True
            except redis.exceptions.ConnectionError:
                logging.error("Unable to connect to Redis server.")
            except BaseException:
                logging.error("Base Except: Unable to connect to Redis server.")
        return return_value

    def delete_key_from_redis_db(self, key):
        return_value = False
        if self.redis_instance:
            try:
                if self.redis_instance.exists(key):
                    if self.redis_instance.delete(key):
                        return_value = True
            except redis.exceptions.ConnectionError:
                logging.error("Unable to connect to Redis server.")
            except BaseException:
                logging.error("Base Except: Unable to connect to Redis server.")
        return return_value

    def increment_key_in_redis_db(self, key):
        return_value = False
        if self.redis_instance:
            try:
                self.redis_instance.incr(key)
                return_value = True
            except redis.exceptions.ConnectionError:
                logging.error("Unable to connect to Redis server.")
            except BaseException:
                logging.error("Base Except: Unable to connect to Redis server.")
        return return_value

    def read_key_value_from_redis_db(self, key):
        return_value = -1
        if self.redis_instance is not None:
            try:
                if self.redis_instance.exists(key):
                    return_value = self.redis_instance.get(key)
            except redis.exceptions.ConnectionError:
                logging.error("Unable to connect to Redis server.")
            except BaseException:
                logging.error("Base Except: Unable to connect to Redis server.")
        return return_value

    def find_keys_matching_a_pattern(self, pattern):
        logging.info("Trying to find all keys matching this pattern {}.".format(pattern))
        return_value = None
        try:
            return_value = self.redis_instance.keys(pattern=(pattern + '*').encode('utf-8'))
        except:
            logging.error("Caught an exception.")
        return return_value

    def get_list_of_values_based_upon_a_key(self, name, key):
        logging.info("Trying to get_list_of_values_based_upon_a_key name={}, key={}."
                     .format(name, key))
        return_value = None
        try:
            return_value = self.redis_instance.hmget(name, key)
        except:
            logging.error("Caught an exception.")
        return return_value

    def set_key_to_value_within_name(self, name, key, value):
        logging.info("Trying to set_key_to_value_within_name name={}, key={}, value={}."
                     .format(name, key, value))
        return_value = None
        try:
            return_value = self.redis_instance.hset(name, key, value)
        except:
            logging.error("Caught an exception.")
        return return_value

    def cleanup(self):
        pass
