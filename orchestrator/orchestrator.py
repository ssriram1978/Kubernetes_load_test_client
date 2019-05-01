# !/usr/bin/env python3
import datetime
import logging
import os
import sys
import time
import traceback
import json

logging.basicConfig(format='%(message)s',
                    level=logging.INFO)


def import_all_paths():
    realpath = os.path.realpath(__file__)
    # print("os.path.realpath({})={}".format(__file__,realpath)`)
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


class Orchestrator:
    """
        This Class is used to orchestrate hundreds of producer, consumer and transformer docker instances.
    """
    publisher_message_starting_port = 50000
    publisher_signaling_starting_port = 51000
    subscriber_message_starting_port = 52000
    subscriber_signaling_starting_port = 53000
    max_number_of_ports = 100

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.container_id = os.popen("cat /proc/self/cgroup | head -n 1 | cut -d '/' -f3").read()
        self.container_id = self.container_id[:12]
        self.is_loopback = None
        self.publisher_container_ids = None
        self.subscriber_container_ids = None
        self.transformer_container_ids = None
        self.publisher_hash_table_name = None
        self.subscriber_hash_table_name = None
        self.transformer_hash_table_name = None
        self.publisher_key_name = None
        self.subscriber_key_name = None
        self.transformer_key_name = None
        self.distribute_ports = None
        self.redis_instance = RedisInterface("Orchestrator")
        self.load_environment_variables()
        self.pub_message_port = Orchestrator.publisher_message_starting_port
        self.pub_signaling_port = Orchestrator.publisher_signaling_starting_port
        self.sub_message_port = Orchestrator.subscriber_message_starting_port
        self.sub_signaling_port = Orchestrator.subscriber_signaling_starting_port

    def set_log_level(self):
        """
        Create Logger.
        :return:
        """
        pass

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.publisher_key_name or \
                not self.subscriber_key_name or \
                not self.transformer_key_name or \
                not self.publisher_hash_table_name or \
                not self.subscriber_hash_table_name or \
                not self.transformer_hash_table_name:
            self.is_loopback = os.getenv("is_loopback_key",
                                         default=None)
            self.publisher_key_name = os.getenv("publisher_key_name",
                                                default=None)
            self.subscriber_key_name = os.getenv("subscriber_key_name",
                                                 default=None)
            self.transformer_key_name = os.getenv("transformer_key_name",
                                                  default=None)
            self.publisher_hash_table_name = os.getenv("publisher_hash_table_name",
                                                       default=None)
            self.subscriber_hash_table_name = os.getenv("subscriber_hash_table_name",
                                                        default=None)
            self.transformer_hash_table_name = os.getenv("transformer_hash_table_name",
                                                         default=None)
            self.distribute_ports = os.getenv("distribute_ports",
                                              default=None)

            time.sleep(1)
        logging.info("is_loopback={},\n"
                     "publisher_key_name={},\n"
                     "subscriber_key_name={},\n"
                     "transformer_key_name={},\n"
                     "publisher_hash_table_name={},\n"
                     "subscriber_hash_table_name={},\n"
                     "distribute_ports={},\n"
                     "transformer_hash_table_name={},\n"
                     .format(self.is_loopback,
                             self.publisher_key_name,
                             self.subscriber_key_name,
                             self.transformer_key_name,
                             self.publisher_hash_table_name,
                             self.subscriber_hash_table_name,
                             self.distribute_ports,
                             self.transformer_hash_table_name))

    def read_all_containers_from_redis(self, key):
        container_list = []
        containers_str = self.redis_instance.get_value_based_upon_the_key(key)
        if not containers_str or containers_str == -1:
            logging.info("Unable to fetch value for key  {}."
                         .format(key))
            return container_list
        container_list = containers_str.decode('utf-8').split()
        return container_list

    def yield_non_assigned_container(self, container_list, hash_table_name):
        for container_id in container_list:
            if not self.redis_instance. \
                    get_list_of_values_based_upon_a_key(hash_table_name,
                                                        container_id)[0]:
                yield container_id

    def populate_publishers_subscribers_hash_tables_with_loopback(self,
                                                                  pub_list,
                                                                  sub_list):
        for pub_container_id in self.yield_non_assigned_container(pub_list,
                                                                  self.publisher_hash_table_name):
            for sub_container_id in self.yield_non_assigned_container(
                    sub_list,
                    self.subscriber_hash_table_name):
                self.redis_instance.set_key_to_value_within_name(
                    self.publisher_hash_table_name,
                    pub_container_id,
                    str({"publisher": "loop_" + pub_container_id}))

                self.redis_instance.set_key_to_value_within_name(
                    self.subscriber_hash_table_name,
                    sub_container_id,
                    str({"subscriber": "loop_" + pub_container_id}))
                break

    def populate_publishers_subscribers_and_transformers_hash_tables(self,
                                                                     pub_list,
                                                                     sub_list,
                                                                     trans_list):
        for pub_container_id in self.yield_non_assigned_container(
                pub_list,
                self.publisher_hash_table_name):

            for sub_container_id in self.yield_non_assigned_container(
                    sub_list,
                    self.subscriber_hash_table_name):
                for trans_container_id in self.yield_non_assigned_container(
                        trans_list,
                        self.transformer_hash_table_name):
                    self.redis_instance.set_key_to_value_within_name(
                        self.publisher_hash_table_name,
                        pub_container_id,
                        str({"publisher": "pub_" + pub_container_id}))

                    self.redis_instance.set_key_to_value_within_name(
                        self.subscriber_hash_table_name,
                        sub_container_id,
                        str({"subscriber": "sub_" + sub_container_id}))

                    self.redis_instance.set_key_to_value_within_name(
                        self.transformer_hash_table_name,
                        trans_container_id,
                        str({"subscriber": "pub_" + pub_container_id,
                             "publisher": "sub_" + sub_container_id}))
                break
            break

    def populate_publishers_subscribers_with_loopback_ports(self,
                                                            pub_list,
                                                            sub_list):
        for pub_container_id in self.yield_non_assigned_container(
                pub_list,
                self.publisher_hash_table_name):
            for sub_container_id in self.yield_non_assigned_container(
                    sub_list,
                    self.subscriber_hash_table_name):
                dict_of_ports = {'PUB': self.pub_message_port,
                                 'REP': self.pub_signaling_port}
                self.redis_instance.set_key_to_value_within_name(
                    self.publisher_hash_table_name,
                    pub_container_id,
                    str({"publisher":
                        json.dumps(
                            dict_of_ports)}))
                dict_of_ports = {'SUB': self.pub_message_port,
                                 'REQ': self.pub_signaling_port}
                self.redis_instance.set_key_to_value_within_name(
                    self.subscriber_hash_table_name,
                    sub_container_id,
                    str({"subscriber":
                        json.dumps(
                            dict_of_ports)}))
                self.pub_message_port += 1
                self.pub_signaling_port += 1
                break

    def populate_publishers_subscribers_and_transformers_hash_tables_with_ports(self,
                                                                                publishers,
                                                                                subscribers,
                                                                                transformers):
        for pub_container_id in self.yield_non_assigned_container(
                publishers,
                self.publisher_hash_table_name):
            for sub_container_id in self.yield_non_assigned_container(
                    subscribers,
                    self.subscriber_hash_table_name):
                for trans_container_id in self.yield_non_assigned_container(
                        transformers,
                        self.transformer_hash_table_name):
                    dict_of_ports = {'PUB': self.pub_message_port,
                                     'REP': self.pub_signaling_port}
                    self.redis_instance.set_key_to_value_within_name(
                        self.publisher_hash_table_name,
                        pub_container_id,
                        str({"publisher":
                            json.dumps(
                                dict_of_ports)}))
                    dict_of_ports = {'SUB': self.sub_message_port,
                                     'REQ': self.sub_signaling_port}

                    self.redis_instance.set_key_to_value_within_name(
                        self.subscriber_hash_table_name,
                        sub_container_id,
                        str({"subscriber":
                            json.dumps(
                                dict_of_ports)}))
                    dict_of_pub_ports = {'PUB': self.sub_message_port,
                                         'REP': self.sub_signaling_port}
                    dict_of_sub_ports = {'SUB': self.pub_message_port,
                                         'REQ': self.pub_signaling_port}
                    self.redis_instance.set_key_to_value_within_name(
                        self.transformer_hash_table_name,
                        trans_container_id,
                        str({"subscriber":
                            json.dumps(
                                dict_of_sub_ports),
                            "publisher":
                                json.dumps(
                                    dict_of_pub_ports)}))
                    self.pub_message_port += 1
                    self.pub_signaling_port += 1
                    self.sub_message_port += 1
                    self.sub_signaling_port += 1
                    break
                break

    def perform_job(self):
        while True:
            publishers = self.read_all_containers_from_redis(self.publisher_key_name)
            subscribers = self.read_all_containers_from_redis(self.subscriber_key_name)
            if self.distribute_ports == "true":
                if self.is_loopback and self.is_loopback == "true":
                    self.populate_publishers_subscribers_with_loopback_ports(publishers,
                                                                             subscribers)
                else:
                    transformers = self.read_all_containers_from_redis(self.transformer_key_name)
                    self.populate_publishers_subscribers_and_transformers_hash_tables_with_ports(publishers,
                                                                                                 subscribers,
                                                                                                 transformers)
            if self.is_loopback and self.is_loopback == "true":
                self.populate_publishers_subscribers_hash_tables_with_loopback(publishers,
                                                                               subscribers)
            else:
                transformers = self.read_all_containers_from_redis(self.transformer_key_name)
                self.populate_publishers_subscribers_and_transformers_hash_tables(publishers,
                                                                                  subscribers,
                                                                                  transformers)

            time.sleep(5)


if __name__ == '__main__':
    orchestrator = Orchestrator()
    try:
        orchestrator.perform_job()
    except KeyboardInterrupt:
        logging.error("Keyboard interrupt." + sys.exc_info()[0])
        logging.error("Exception in user code:")
        logging.error("-" * 60)
        traceback.print_exc(file=sys.stdout)
        logging.error("-" * 60)
