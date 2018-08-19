# arista_sd
Custom Prometheus service discovery to get arista switch hostnames of baremetal PODs from [Netbox](https://netbox.readthedocs.io/en/latest/).   
The targets are written into a configmap.

## Prerequisites and Installation

The service discovery was written for Python 3.6 or newer. To install all modules needed you have to run the following command:

```bash
pip3 install --no-cache-dir -r requirements.txt
```

There is also a docker file available to create a docker container to run the exporter.

