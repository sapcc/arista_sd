import argparse
from yamlconfig import YamlConfig
from urllib.request import urlopen
from kubernetes import client, config
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
        self._region = os.environ['region'].lower()
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

def get_config():
    # get the config from the config file
    myconfig = YamlConfig(args.config)

    # get the config of the k8s cluster
    try:
        config.load_kube_config()

    except IOError:
        config.load_incluster_config()

    myconfig['refresh_interval'] = os.environ['REFRESH_INTERVAL'] or myconfig['refresh_interval']
    
    if os.environ['OS_PROM_CONFIGMAP_NAME']:
        myconfig['configmap_name'] = os.environ['OS_PROM_CONFIGMAP_NAME']
    else:
        logging.error("No configmap name in environment!")
        exit(1)

    try:
        v1 = client.CoreV1Api()
        config_map = v1.read_namespaced_config_map(myconfig['configmap_name'], myconfig['namespace'])
        config_map.data = {}
        
    
    except client.rest.ApiException:
        logging.error("No configmal received!")
        exit(1)

    return myconfig

if __name__ == '__main__':

    app_environment = os.environ['APP_ENV'].lower()
    # command line options
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="Specify config yaml file", metavar="FILE", required=False, default="config.yml")
    args = parser.parse_args()

    myconfig = get_config()

    # enable logging
    logger = logging.getLogger()
    if app_environment == "production":
        logger.setLevel('INFO')
    else:
        logger.setLevel('DEBUG')
    format = '%(asctime)-15s %(process)d %(levelname)s %(filename)s:%(lineno)d %(message)s'
    logging.basicConfig(stream=sys.stdout, format=format)

    mydiscovery = discovery(myconfig)

    while True:
        devices = mydiscovery.get_devices()

        logging.debug("Devices: %s", devices)


        # Write the configmap file
        labels = {'job': myconfig['job']}
        result = {'targets': devices, 'labels': labels}
        configmap = [result]

        with open(myconfig['configmap'], 'w') as outfile:
            json.dump(configmap, outfile, indent=2)
    
        time.sleep(myconfig['refresh_interval'])