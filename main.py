import argparse
from yamlconfig import YamlConfig
from urllib.request import urlopen
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging
import sys
import socket
import re
import ssl
import json
import os
import time

class discovery(object):
    def __init__(self, config):
        self._region = config['region']
        self._netbox = config['netbox']
        self._dnssuffix = ".cc.{0}.cloud.sap".format(self._region)
        self.check_region()

    def check_region(self):
        region_regex = re.compile(r'[a-z]{2}-[a-z]{2}-\d')
        logging.debug("Using regex: %s", region_regex)

        if not re.fullmatch(region_regex, self._region):
            logging.error("""Region '%s' is not a valid region""", self._region)
            exit(1)

    def filter_devices(self, devices):
        name_regex = re.compile(r'%s-asw20\d-bm\d{3}' % (self._region))
        logging.debug("Using regex: %s", name_regex)
        logging.info("Devices before: {0}".format(len(devices)))

        selected_devices = [item['name']+self._dnssuffix for item in devices if re.fullmatch(name_regex, item['name'])]

        logging.info("Devices filtered: {0}".format(len(selected_devices)))

        return selected_devices

    def get_devices(self):
        query_string = "asw20"
        manufacturer_id = "6"

        netbox_url = "https://{0}/api/dcim/devices/?q={1}&manufacturer_id={2}".format(self._netbox, query_string, manufacturer_id)

        # switch off certificate validation
        ssl._create_default_https_context = ssl._create_unverified_context

        devices_url = urlopen(netbox_url)
        devices = json.loads(devices_url.read().decode('utf8'))['results']
        logging.info("Devices found: {0}".format(len(devices)))

        filtered_devices = self.filter_devices(devices=devices)
        return filtered_devices

def write_configmap(myconfig, devices):

    # get the config of the k8s cluster
    # try locally and if not working then from the cluster running in
    try:
        config.load_kube_config()

    except IOError:
        config.load_incluster_config()

    # Get the configmap
    try:
        api_instance = client.CoreV1Api()
        config_map = api_instance.read_namespaced_config_map(myconfig['configmap_name'], myconfig['namespace'])
        config_map.data = {}
    except client.rest.ApiException as e:
        logging.error("No configmap received! (%s)", e)
        exit(1)

    # Put the json together
    labels = {'job': myconfig['job']}
    result = {'targets': devices, 'labels': labels}
    configmap = [result]

    config_map.data[myconfig['configmap']] = json.dumps(configmap, indent=2)

    # Write the configmap
    try:
        response = api_instance.patch_namespaced_config_map(myconfig['configmap_name'], myconfig['namespace'], config_map, pretty=True)
        logging.debug("Response: %s", response)
    except client.rest.ApiException as e:
        logging.error("Exception while updating configmap!(%s)", e)
        exit(1)

def get_config(configfile):
    # get the config from the config file and environment
    config = YamlConfig(configfile)
    config['refresh_interval'] = os.getenv('REFRESH_INTERVAL', config['refresh_interval'])

    if os.getenv('OS_PROM_CONFIGMAP_NAME'):
        config['configmap_name'] = os.environ['OS_PROM_CONFIGMAP_NAME']
    else:
        logging.error("No configmap name in environment!")
        exit(1)

    if os.getenv('region'):
        config['region'] = os.environ['region'].lower()
    else:
        logging.error("No region in environment!")
        exit(1)

    return config

def enable_logging():
    # enable logging
    logger = logging.getLogger()
    app_environment = os.getenv('APP_ENV', default="production").lower()
    if app_environment == "production":
        logger.setLevel('INFO')
    else:
        logger.setLevel('DEBUG')
    format = '%(asctime)-15s %(process)d %(levelname)s %(filename)s:%(lineno)d %(message)s'
    logging.basicConfig(stream=sys.stdout, format=format)

if __name__ == '__main__':

    # command line options
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="Specify config yaml file", metavar="FILE", required=False, default="config.yml")
    args = parser.parse_args()
    enable_logging()

    myconfig = get_config(args.config)
    logging.debug("Config: %s", myconfig)
    mydiscovery = discovery(myconfig)

    while True:
        devices = mydiscovery.get_devices()
        logging.debug("Devices: %s", devices)
        write_configmap(myconfig, devices)
  
        time.sleep(myconfig['refresh_interval'])