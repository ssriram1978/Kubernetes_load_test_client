# !/usr/bin/env python3
import logging
import os
import sys

logging.basicConfig(format='%(levelname)s:%(asctime)s:%(message)s',
                    level=logging.INFO,
                    datefmt='%m/%d/%Y %I:%M:%S %p')


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


class Plotter:
    """
        This Class is used to plot latency on Grafana via prometheus.
    """

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.load_environment_variables()
        self.redis_instance = RedisInterface("Plotter")
        self.topic = None

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        pass

    def perform_job(self):
        if self.redis_instance:
            value = self.redis_instance.get_list_of_values_based_upon_a_key(topic, str(dt))[0]
