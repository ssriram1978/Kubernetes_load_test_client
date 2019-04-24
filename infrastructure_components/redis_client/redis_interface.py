import logging
import os
import sys
import time


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

from infrastructure_components.redis_client.redis_client import RedisClient


class RedisInterface(object):
    """
    This class does the following:
    """

    def __init__(self, thread_identifer=None):
        logging.info("Instantiating RedisInterface for {}.".format(thread_identifer))
        self.total_job_enqueued_count_redis_name = None
        self.total_job_dequeued_count_redis_name = None
        self.redis_log_keyname = None
        self.thread_identifer = thread_identifer
        self.read_environment_variables()
        self.redis_instance = RedisClient()

    def read_environment_variables(self):
        """
        This method is used to read the environment variables
        defined in the OS.
        :return:
        """
        while not self.redis_log_keyname:
            time.sleep(2)
            logging.debug("RedisInterface:{} "
                          "Trying to read the "
                          "environment variables..."
                          .format(self.thread_identifer))
            self.redis_log_keyname = os.getenv("redis_log_keyname_key",
                                               default=None)
            self.total_job_enqueued_count_redis_name = os.getenv("total_job_enqueued_count_redis_name_key",
                                                                 default="total_job_enqueued_count")
            self.total_job_dequeued_count_redis_name = os.getenv("total_job_dequeued_count_redis_name_key",
                                                                 default="total_job_dequeued_count")
        logging.debug("RedisInterface:{} "
                      "redis_log_keyname={}, "
                      "total_job_enqueued_count_redis_name={}, "
                      "total_job_dequeued_count_redis_name={}. "
                      .format(self.thread_identifer,
                              self.redis_log_keyname,
                              self.total_job_enqueued_count_redis_name,
                              self.total_job_dequeued_count_redis_name))

    def get_current_enqueue_count(self):
        count = self.redis_instance.read_key_value_from_redis_db(self.total_job_enqueued_count_redis_name)
        logging.debug("RedisInterface:{}."
                      "{}={}"
                      .format(self.thread_identifer,
                              self.total_job_enqueued_count_redis_name,
                              count))
        return count

    def get_current_dequeue_count(self):
        count = self.redis_instance.read_key_value_from_redis_db(self.total_job_dequeued_count_redis_name)
        logging.debug("RedisInterface:{}."
                      "{}={}"
                      .format(self.thread_identifer,
                              self.total_job_dequeued_count_redis_name,
                              count))
        return count

    def increment_enqueue_count(self):
        logging.debug("RedisInterface:{}."
                      "Incrementing total_job_enqueued_count={}"
                      .format(self.thread_identifer,
                              self.total_job_enqueued_count_redis_name))
        self.redis_instance.increment_key_in_redis_db(self.total_job_enqueued_count_redis_name)

    def increment_dequeue_count(self):
        logging.debug("RedisInterface:{}."
                      "Incrementing total_job_dequeued_count={}"
                      .format(self.thread_identifer,
                              self.total_job_dequeued_count_redis_name))
        self.redis_instance.increment_key_in_redis_db(self.total_job_dequeued_count_redis_name)

    def check_if_the_key_exists_in_redis_db(self, key):
        logging.debug("RedisInterface:{}."
                      "check_if_the_key_exists_in_redis_db key={}"
                      .format(self.thread_identifer,
                              key))
        return self.redis_instance.check_if_the_key_exists_in_redis_db(key)

    def set_the_key_in_redis_db(self, key, value=1):
        logging.debug("RedisInterface:{}."
                      "set_the_key_in_redis_db {}={}"
                      .format(self.thread_identifer,
                              key,
                              value))
        return self.redis_instance.set_the_key_in_redis_db(key, value)

    def write_an_event_in_redis_db(self, event):
        logging.debug("RedisInterface:{}."
                      "Writing at key={}"
                      " event={}"
                      .format(self.thread_identifer,
                              self.redis_log_keyname,
                              event))
        self.redis_instance.write_an_event_on_redis_db(event, self.redis_log_keyname)

    def find_keys_matching_a_pattern(self, pattern):
        logging.debug("Trying to find all keys matching this pattern {}.".format(pattern))
        return self.redis_instance.find_keys_matching_a_pattern(pattern)

    def get_list_of_values_based_upon_a_key(self, name, key):
        logging.debug("Trying to get_list_of_values_based_upon_a_key name={}, key={}."
                      .format(name, key))
        return self.redis_instance.get_list_of_values_based_upon_a_key(name, key)

    def set_key_to_value_within_name(self, name, key, value):
        logging.debug("Trying to set_key_to_value_within_name name={}, key={}, value={}."
                      .format(name, key, value))
        return self.redis_instance.set_key_to_value_within_name(name, key, value)

    def append_value_to_a_key(self, key, value):
        logging.debug("Trying to append_value_to_a_key key={}, value={}."
                      .format(key, value))
        return self.redis_instance.append_value_to_a_key_in_redis_db(key, value)

    def get_value_based_upon_the_key(self, key):
        value = self.redis_instance.read_key_value_from_redis_db(key)
        logging.debug("RedisInterface:{}."
                      "{}={}"
                      .format(self.thread_identifer,
                              key,
                              value))
        return value

    def cleanup(self):
        pass
