# !/usr/bin/env python3
import datetime
import logging
import os
import sys
import time
import traceback
import json
import dateutil.parser
import matplotlib.pyplot as plt
import mpld3
from matplotlib import dates
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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
    ip_address_of_host = None
    port_number_of_host = 0
    html_filename = "latency.html"

    def __init__(self):
        """
        Initialize the class instance variables.
        """
        self.redis_instance = RedisInterface("Plotter")
        self.latency_redis_key = None
        self.latency_redis_start_key = None
        self.latency_compute_start_key_name = None
        self.load_environment_variables()
        self.start_consumer_thread()

    def load_environment_variables(self):
        """
        Load environment variables.
        :return:
        """
        while not self.latency_redis_key or \
                not Plotter.ip_address_of_host or \
                not Plotter.port_number_of_host or \
                not self.latency_compute_start_key_name:
            time.sleep(1)
            self.latency_redis_key = os.getenv("latency_redis_key",
                                               default=None)
            self.latency_redis_start_key = os.getenv("latency_redis_start_key",
                                                     default="start_time")
            Plotter.ip_address_of_host = os.getenv("ip_address_of_host_key",
                                                   default='0.0.0.0')
            Plotter.port_number_of_host = int(os.getenv("port_number_of_host_key",
                                                        default='8888'))

            self.latency_compute_start_key_name = os.getenv("latency_compute_start_key_name_key",
                                                            default=None)
        logging.debug(("latency_redis_key={},\n"
                       "ip_address_of_host={},\n"
                       "port_number_of_host={},\n"
                       "latency_redis_start_key={},\n"
                       "latency_compute_start_key_name={}."
                       .format(self.latency_redis_key,
                               Plotter.ip_address_of_host,
                               Plotter.port_number_of_host,
                               self.latency_redis_start_key,
                               self.latency_compute_start_key_name)))

    def convert_timestamp_from_string_to_obj(self, timestamp_in_string_format):
        timestamp_obj = None
        try:
            timestamp_obj = dateutil.parser.parse(timestamp_in_string_format)
        except:
            logging.debug("Unable to decode {} into a timestamp object.".format(timestamp_in_string_format))
        return timestamp_obj

    def go_to_the_next_second(self, timestamp_in_string_format):

        timestamp_obj = self.convert_timestamp_from_string_to_obj(timestamp_in_string_format)

        year = timestamp_obj.year
        month = timestamp_obj.month
        day = timestamp_obj.day
        hour = timestamp_obj.hour
        minute = timestamp_obj.minute
        second = timestamp_obj.second

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

        ts_obj = datetime.datetime(year=year,
                                   month=month,
                                   day=day,
                                   hour=hour,
                                   minute=minute,
                                   second=second)
        return str(ts_obj.isoformat(timespec='seconds'))

    def obtain_starting_timestamp(self, hash_table_name):
        is_first_timestamp_obtained = False
        timestamp = None
        while not is_first_timestamp_obtained:
            try:
                timestamp = self.redis_instance.get_list_of_values_based_upon_a_key(
                    hash_table_name, self.latency_redis_start_key)[0].decode('utf-8')
                if timestamp:
                    logging.info("Obtained the first starting time as {}."
                                 .format(timestamp))
                    is_first_timestamp_obtained = True
            except:
                logging.info("Unable to find {} in hash table {} in redis."
                             .format(self.latency_redis_start_key, hash_table_name))
                time.sleep(1)
                continue
        return timestamp

    def read_latency_from_redis(self, hash_table_name):
        null_data_retry_attempts = 10
        current_retry_attempts = 0
        starting_ts = self.obtain_starting_timestamp(hash_table_name)

        ts_obj = self.convert_timestamp_from_string_to_obj(starting_ts)

        date_time = str(ts_obj.isoformat(timespec='seconds'))

        while True:
            latency_list = self.redis_instance. \
                get_list_of_values_based_upon_a_key(hash_table_name, date_time)
            if not latency_list[0]:
                if current_retry_attempts >= null_data_retry_attempts:
                    logging.debug("Giving up...Breaking from the loop because there is no value for the key{}"
                                  .format(date_time))
                    break
                else:
                    current_retry_attempts += 1
                    logging.debug("There is no value for the key{}, waiting for a second to fetch new data."
                                  .format(date_time))
                    time.sleep(1)
                    continue
            else:
                current_retry_attempts = 0
                dict_data = {'originated_timestamp': date_time, 'latency': eval(latency_list[0].decode('utf-8'))}
                logging.info("{}".format(json.dumps(dict_data, ensure_ascii=False)))
                self.pyplot_mpld3(ts_obj, eval(latency_list[0].decode('utf-8')))
                date_time = self.go_to_the_next_second(date_time)
                ts_obj = self.convert_timestamp_from_string_to_obj(date_time)

    def perform_job(self):
        if self.redis_instance:
            key_found = False
            list_of_keys_with_latency_compute_name = None
            while not key_found:
                list_of_keys_with_latency_compute_name = \
                    self.redis_instance.get_value_based_upon_the_key(self.latency_redis_key)
                if not list_of_keys_with_latency_compute_name or \
                        list_of_keys_with_latency_compute_name == -1:
                    logging.info("Unable to find any keys matching {} in redis.{}" \
                                 .format(self.latency_redis_key, list_of_keys_with_latency_compute_name))
                    time.sleep(1)
                else:
                    logging.info("Found a key:{}, value:{}.".format(self.latency_redis_key,
                                                                    list_of_keys_with_latency_compute_name))
                    key_found = True
            list_of_keys_with_latency_compute_name = list_of_keys_with_latency_compute_name.decode('utf-8').split()
            for latency_compute_key in list_of_keys_with_latency_compute_name:
                if not len(latency_compute_key) or latency_compute_key == ' ':
                    continue
                logging.info("Trying to fetch the hashtable {}.".format(latency_compute_key))
                self.read_latency_from_redis(latency_compute_key)

        # mpld3.show(ip=self.ip_address_of_host,
        #           port=self.port_number_of_host,
        #           open_browser=False)

    def cleanup(self):
        pass

    @staticmethod
    def run_consumer_thread(*args, **kwargs):
        print("Starting {}".format(threading.current_thread().getName()))
        server_class = HTTPServer
        httpd = server_class((Plotter.ip_address_of_host, Plotter.port_number_of_host), MyHandler)
        print(time.asctime(), 'Server Starts - %s:%s' % (Plotter.ip_address_of_host, Plotter.port_number_of_host))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        print(time.asctime(), 'Server Stops - %s:%s' % (Plotter.ip_address_of_host, Plotter.port_number_of_host))

        print("Thread {}: Exiting"
              .format(threading.current_thread().getName()))

    def start_consumer_thread(self):
        consumer_thread = threading.Thread(name="plotter_thread",
                                           target=Plotter.run_consumer_thread,
                                           args=(),
                                           kwargs={})
        consumer_thread.do_run = True
        consumer_thread.name = "plotter"
        consumer_thread.start()

    def pyplot_mpld3(self, timestamp, list_of_latencies):
        plt.xlabel("Time --> Day:Hour:Minute:Second", style='normal', color='red', fontsize='24')
        plt.ylabel("Latency --> (milliseconds)", style='normal', color='red', fontsize='24')
        plt.title("Latency (milliseconds) vs Time", style='normal', color='red', fontsize='24')
        matplot_date = dates.date2num(timestamp)
        plt.figure(figsize=(4.0, 4.0), dpi=400)
        for value in list_of_latencies:
            plt.plot_date(xdate=True, x=matplot_date, y=value, tz='America/New_York')
        mpld3.save_html(fig=plt.gcf(), fileobj=Plotter.html_filename, template_type='simple', use_http=True)
        # plt.legend()
        plt.autoscale()


class MyHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self.respond({'status': 200})

    def handle_http(self, status_code, path):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        content = None
        with open(Plotter.html_filename, "r", encoding='utf-8') as f:
            content = f.read()
        return bytes(content, 'UTF-8')

    def respond(self, opts):
        response = self.handle_http(opts['status'], self.path)
        self.wfile.write(response)


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
