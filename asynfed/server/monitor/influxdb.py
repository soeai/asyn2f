from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from asynfed.common.messages.client import ClientModelUpdate

import logging
LOGGER = logging.getLogger(__name__)

class InfluxDB():
    def __init__(self, config: dict):
        """
        config = {
            "url": "http://localhost:8086",
            "token": "",
            "org": "ttu",
            "bucket_name": "tester",
        }
        """
        self.client = InfluxDBClient(url=config['url'], token=config['token'], org=config['org'])
        self.bucket_name = config['bucket_name']
        self.org = config['org']
        self._create_bucket(self.bucket_name)


    def _create_bucket(self, bucket_name):
        try:
            bucket_api = self.client.buckets_api()
            bucket_api.create_bucket(bucket_name=bucket_name)
        except Exception as e:
            if 'already exists' in e.message:
                pass
            else:
                LOGGER.info("Error: {}".format(e))

    # def write_training_process_data(self, msg_received):
    def write_training_process_data(self, timestamp, client_id: str, client_model_update: ClientModelUpdate):
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        measurement = client_id

        record = (
            Point(measurement)
            .field("client_id", client_id)
            .field("train_acc", client_model_update.performance)
            .field("train_loss", client_model_update.loss)
            .time(timestamp, WritePrecision.NS)
        )


        try:
            write_api.write(bucket=self.bucket_name, org=self.org, record=record)
        except Exception as e:
            LOGGER.error(e)
