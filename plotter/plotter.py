# !/usr/bin/env python3
import datetime
import logging
import os
import sys
import time
import traceback
import json
import dateutil.parser
import matplotlib.pyplot as plt, mpld3
from matplotlib import dates

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


class Plotter:
    """
        This Class is used to plot latency on Grafana via prometheus.
    """

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.redis_instance = RedisInterface("Plotter")
        self.latency_redis_key = None
        self.latency_compute_start_key_name = None
        self.ip_address_of_host = None
        self.port_number_of_host = 0
        self.load_environment_variables()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.latency_redis_key or \
                not self.ip_address_of_host or \
                not self.port_number_of_host or \
                not self.latency_compute_start_key_name:
            time.sleep(1)
            self.latency_redis_key = os.getenv("latency_redis_key",
                                               default=None)
            self.ip_address_of_host = os.getenv("ip_address_of_host_key",
                                                default='0.0.0.0')
            self.port_number_of_host = int(os.getenv("port_number_of_host_key",
                                                     default='8888'))

            self.latency_compute_start_key_name = os.getenv("latency_compute_start_key_name_key",
                                                            default=None)
        logging.debug(("latency_redis_key={},\n"
                       "ip_address_of_host={},\n"
                       "port_number_of_host={},\n"
                       "latency_compute_start_key_name={}."
                       .format(self.latency_redis_key,
                               self.ip_address_of_host,
                               self.port_number_of_host,
                               self.latency_compute_start_key_name)))

    def perform_job(self):
        is_first_timestamp_obtained = False
        timestamp = None
        ts = None
        if self.redis_instance:
            while not is_first_timestamp_obtained:
                try:
                    timestamp = self.redis_instance.get_value_based_upon_the_key(
                        self.latency_compute_start_key_name).decode('utf-8')
                    if timestamp:
                        logging.debug("Obtained the first starting time as {}"
                                      .format(timestamp))
                        is_first_timestamp_obtained = True
                except:
                    logging.debug("Unable to find a key {} in redis."
                                  .format(self.latency_compute_start_key_name))
                    time.sleep(1)
                    continue
            try:
                ts = dateutil.parser.parse(timestamp)
            except:
                logging.debug("Unable to parse {}.".format(timestamp))
                return
            dt = str(ts.isoformat(timespec='seconds'))

            null_data_retry_attempts = 60
            current_retry_attempts = 0
            while True:
                latency_list = self.redis_instance. \
                    get_list_of_values_based_upon_a_key(self.latency_redis_key, dt)
                if not latency_list[0]:
                    if current_retry_attempts >= null_data_retry_attempts:
                        logging.debug("Giving up...Breaking from the loop because there is no value for the key{}"
                                      .format(dt))
                        break
                    else:
                        current_retry_attempts += 1
                        logging.debug("There is no value for the key{}, waiting for a second to fetch new data."
                                      .format(dt))
                        time.sleep(1)
                        continue
                else:
                    current_retry_attempts = 0
                    dict_data = {'originated_timestamp': dt, 'latency': eval(latency_list[0].decode('utf-8'))}
                    logging.info("{}".format(json.dumps(dict_data, ensure_ascii=False)))
                    self.pyplot_mpld3(ts, eval(latency_list[0].decode('utf-8')))

                year = ts.year
                month = ts.month
                day = ts.day
                hour = ts.hour
                minute = ts.minute
                second = ts.second

                if second == 59:
                    second = 0
                    minute += 1
                else:
                    second += 1
                if minute == 60:
                    minute = 0
                    hour += 1
                if hour == 24:
                    hour = 0
                    day += 1
                if day == 28:
                    day = 0
                    month += 1
                if month == 12:
                    month = 1
                    year += 1

                ts = datetime.datetime(year=year,
                                       month=month,
                                       day=day,
                                       hour=hour,
                                       minute=minute,
                                       second=second)
                dt = str(ts.isoformat(timespec='seconds'))
        mpld3.show(ip=self.ip_address_of_host,
                   port=self.port_number_of_host,
                   open_browser=False)

    def cleanup(self):
        pass

    def pyplot_mpld3(self, timestamp, list_of_latencies):
        plt.xlabel("timestamp", style='normal', fontsize='24')
        plt.ylabel("latency", style='normal', fontsize='24')
        plt.title("Latency vs time", style='normal', fontsize='24')
        matplot_date = dates.date2num(timestamp)
        for value in list_of_latencies:
            plt.plot_date(xdate=True, x=matplot_date, y=value, tz='America/New_York')
        plt.legend()
        plt.autoscale()


if __name__ == '__main__':
    plotter = Plotter()
    try:
        plotter.perform_job()
    except KeyboardInterrupt:
        logging.error("Keyboard interrupt." + sys.exc_info()[0])
        logging.error("Exception in user code:")
        logging.error("-" * 60)
        traceback.print_exc(file=sys.stdout)
        logging.error("-" * 60)
