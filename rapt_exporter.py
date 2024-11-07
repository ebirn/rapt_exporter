import os
import requests
from prometheus_client import Info, CollectorRegistry, Gauge, write_to_textfile, disable_created_metrics, push_to_gateway

import http.client as http_client
import time
from datetime import datetime, timedelta

import logging
logger = logging.getLogger("rapt_exporter")


# http debugging
http_client.HTTPConnection.debuglevel = 0

RAPT_EXPORTER_VERSION="0.0.1"
# init logging
# You must initialize logging, otherwise you'll not see debug output.

logging.basicConfig(
    level = os.environ.get("RAPT_LOG_LEVEL", logging.INFO),
    format = '%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)



#requests_log = logging.getLogger("requests.packages.urllib3")
#requests_log.setLevel(logging.DEBUG)
#requests_log.propagate = True


url_hydrometer_list="https://api.rapt.io/api/Hydrometers/GetHydrometers"
url_hydrometer_telemetry='https://api.rapt.io/api/Hydrometers/GetTelemetry'

url_token="https://id.rapt.io/connect/token"


token_username=os.environ.get('RAPT_USERNAME', 'USERNAME_MISSING')
token_api_key=os.environ.get('RAPT_API_KEY', 'API_KEY_MISSING')
push_gateway_url=os.environ.get('RAPT_PUSH_GATEWAY_URL', 'prometheus-pushgateway:9091')

# max 5 requests per minute
sleep_time=int(os.environ.get('RAPT_LOOP_SLEEP_TIME', 30))



registry = CollectorRegistry()
disable_created_metrics()

token_renew = datetime.now()
token_data = None
# dict per id of collected object
last_metrics_time = {}


# define metrics
hydrometer_label_names = ['id', 'name', 'macAddress']

info_version = Info('rapt_build_version', 'Description of info', registry=registry)
info_version.info({'version': RAPT_EXPORTER_VERSION})

# info_info = Info('rapt_hydrometer_info', 'Hydrometer info', hydrometer_label_names + ['firmwareVersion'], registry=registry)

gauge_fw_version = Gauge('rapt_hydrometer_firmware_version', 'Hydrometer firmware version', hydrometer_label_names, registry=registry)
gauge_temp = Gauge('rapt_hydrometer_temperature', 'Hydrometer temperature', hydrometer_label_names, registry=registry)
gauge_gravity = Gauge('rapt_hydrometer_gravity', 'Hydrometer gravity', hydrometer_label_names, registry=registry)
gauge_battery = Gauge('rapt_hydrometer_battery', 'Hydrometer battery', hydrometer_label_names, registry=registry)
gauge_rssi = Gauge('rapt_hydrometer_rssi', 'Hydrometer rssi', hydrometer_label_names, registry=registry)
gauge_disabled = Gauge('rapt_hydrometer_disabled', 'Hydrometer is disabled', hydrometer_label_names, registry=registry)


def renew_token():
    global token_data
    global token_renew
    logger.info("fetching token...")
    token_form_data = {
        "client_id":"rapt-user",
        "grant_type":"password",
        "username": f"{token_username}",
        "password": f"{token_api_key}",
    }
    token_res = requests.post(url_token, data = token_form_data)
    if token_res.ok:
        logger.info("Token received")
        token_data = token_res.json()
        max_life = timedelta(seconds=token_data['expires_in']) - timedelta(minutes=5)
        token_renew = datetime.now() + max_life
    else:
        logger.error("Token request failed")
        logger.error(f"Error (status {token_res.status_code}): ", token_res.json()['error_description'])
        token_data = None
    
    return token_data


def make_hydrometer_metrics(hydrometer_data):
    # {'temperature': 31, 
    # 'gravity': 759.941, 
    # 'battery': 0, 
    # 'name': 'Stefans Pill', 
    # 'macAddress': '78-e3-6d-27-6c-98', 
    # 'deviceType': 'Hydrometer', 
    # 'active': False, 
    # 'disabled': False, 
    # 'lastActivityTime': '2024-11-06T20:33:45.2292014+00:00', 
    # 'rssi': -38, 
    # 'firmwareVersion': '20240821_062109_0205ab7', 
    # 'isLatestFirmware': False, 
    # 'modifiedOn': '2024-11-06T16:13:17.9938207+00:00', 
    # 'modifiedBy': '00000000-0000-0000-0000-000000000000', 
    # 'id': '9cfdee92-bfe1-4afa-a149-18ad74737905', 
    # 'deleted': False, 
    # 'createdOn': '2024-11-06T16:13:17.9877031+00:00', 
    # 'createdBy': 'c2826c20-79b5-4357-e5d6-08dcf8bdab0b'}
    
    hydrometer_labels = {
        "id": hydrometer_data['id'], 
        "name": hydrometer_data['name'], 
        "macAddress": hydrometer_data['macAddress']
    }

    gauge_fw_version.labels(**hydrometer_labels).set(hydrometer_data['isLatestFirmware'])
    gauge_temp.labels(**hydrometer_labels).set(hydrometer_data['temperature'])   # Set to a given value
    gauge_gravity.labels(**hydrometer_labels).set(hydrometer_data['gravity'])   # Set to a given value
    gauge_battery.labels(**hydrometer_labels).set(hydrometer_data['battery'])   # Set to a given value
    gauge_rssi.labels(**hydrometer_labels).set(hydrometer_data['rssi'])   # Set to a given value
    gauge_disabled.labels(**hydrometer_labels).set(hydrometer_data['disabled']) 
    pass


def renew_expired_token():
    # logger.info("Checking if token needs to be renewed")
    
    renew_required = token_renew <= datetime.now()
    if renew_required:
        logger.info("Token expired, need to renew")
        renew_token()
    if token_data is None:
        logger.info("No token available")
        renew_token()
    else:
        logger.info("Token still valid")
    return

from prometheus_client.exposition import (
    default_handler,
    basic_auth_handler,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


# see gist https://gist.github.com/f41gh7/85b2eb895bb63b93ce46ef73448c62d0?permalink_comment_id=3597154#gistcomment-3597154
def push_to_victoriametrics(url, job, registry, metrics_datetime=datetime.now(), timeout=30, handler=default_handler):
    url = f"{url}?extra_label=job={job}&timestamp={ int(metrics_datetime.timestamp()*1000) }"   #?extra_label=job={job}"  # &extra_label=instance={INSTANCE}
    data = generate_latest(registry)
    handler(
        url=url,
        method="POST",
        timeout=timeout,
        headers=[("Content-Type", CONTENT_TYPE_LATEST)],
        data=data,
    )()
    

def main_loop():
    global token_data
    renew_expired_token()

    if token_data is not None:
        logger.info("fetching hydrometer list...")
        auth_header = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
        hydro_res = requests.get(url_hydrometer_list, headers=auth_header)

        if hydro_res.ok:
            hydro_list = hydro_res.json()
            logger.debug(f"Hydrometer list received: {len(hydro_list)} hydrometers")
            for hydrometer in hydro_list:
                logger.info(f"  processing Hydrometer: {hydrometer['name']}")

                # ?hydrometerId=1&startDate=2024-11-05&endDate=2024-012-01
                # query_params = f"?hydrometerId={ hydrometer['id'] }&startDate=2024-11-05&endDate=2024-11-08"
                # hydro_telemetry_res = requests.get(url_hydrometer_telemetry + query_params, headers=auth_header)
                # print(hydro_telemetry_res.text)
                try:
                    this_metrics_time = datetime.fromisoformat(hydrometer['lastActivityTime'])
                    prev_metrics_time = last_metrics_time.get(hydrometer['id'], datetime.fromisoformat("2000-01-01T00:00:00+00:00"))
                    if this_metrics_time > prev_metrics_time:
                        import json
                        logger.debug("  data: %s", json.dumps(hydrometer))
                        make_hydrometer_metrics(hydrometer)
                        #write_to_textfile('/tmp/hello.prom', registry)
                        # push_to_gateway('http://10.9.0.10:8428', job='rapt', registry=registry)
                        logger.info("  new metrics, from %s", this_metrics_time)
                        push_to_victoriametrics(push_gateway_url, job='rapt', metrics_datetime=this_metrics_time, registry=registry, timeout=30, handler=default_handler)
                        last_metrics_time[hydrometer['id']] = this_metrics_time
                    else:
                        logger.info("  no new metrics, still current from %s", prev_metrics_time)
                        pass
                    
                    logger.info("  done.")

                except Exception as e:
                    logger.error(f"Error processing hydrometer {hydrometer['name']}: {e}")
                    logger.error(f"failed on hydrometer: {hydrometer}")
        else:
            logger.error("Hydrometer list request failed")
            logger.error(f"Error (status {hydro_res.status_code}): ", hydro_res.text)
            if hydro_res.status_code == 401:
                logger.error("Token invalid, resetting...")
                token_data = None
    else:    
        logger.warn("No token available")
    
    logger.info(f"sleeping for {sleep_time} seconds...")
    time.sleep(sleep_time)
    pass

if __name__ == "__main__":
    # Start the server to expose the metrics.
    while True:
        main_loop()
    pass