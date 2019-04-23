# !/usr/bin/env python3
import datetime
import logging
import os
import sys
import time
import traceback

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

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.redis_instance = RedisInterface("Orchestrator")
        self.load_environment_variables()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        pass
        """
        while not :
            time.sleep(1)
        logging.debug(("={},\n"                       
                       .format()))
                               
        """

    def perform_job(self):
        while True:
            time.sleep(1)


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
