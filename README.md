# arista_sd

Custom Prometheus service discovery to get arista switch hostnames of baremetal PODs from [Netbox](https://netbox.readthedocs.io/en/latest/).  
The targets are written into a configmap.

## Prerequisites and Installation

The service discovery was written for Python 3.6 or newer. To install all modules needed you have to run the following command:

```bash
pip3 install --no-cache-dir -r requirements.txt
```

There is also a docker file available to create a docker container to run the exporter.

### Example of a config file

* The **netbox** entry is pointing at the url of the netbox installation.
* **configmap** is the name of the configmap file to write to. The actual configmap name has to be passed via environment variable `OS_PROM_CONFIGMAP_NAME`.
* The **job** parameter specifies the Prometheus job that will be passed as label.
* The **refresh_interval** (in seconds) can either be specified via config file or via environment variable `REFRESH_INTERVAL`. The environment overwrites the setting in the config file.
* **namespace** is the Prometheus Name Space

```text
netbox: netbox.global.cloud.sap
configmap: arista_targets.json
job: arista
refresh_interval: 1800
namespace: kube-monitoring
```
