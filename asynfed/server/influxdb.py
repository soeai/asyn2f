from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import logging
LOGGER = logging.getLogger(__name__)

class InfluxDB():
    def __init__(self, config: dict):
        """
        config = {
            "url": "http://localhost:8086",
            "token": "",
            "org": "ttu",
            "bucket_name": "test",
        }
        """
        self.client = InfluxDBClient(url=config['url'], token=config['token'], org=config['org'])
        self.bucket_name = config['bucket_name']
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

    def write_training_process_data(self, msg_received):
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        measurement = msg_received['headers']['client_id']

        record = (
            Point(measurement)
            .field("client_id", msg_received['headers']['client_id'])
            .field("train_acc", msg_received['content']['performance'])
            .field("train_loss", msg_received['content']['loss'])
            .time(msg_received['headers']['timestamp'], WritePrecision.NS)
        )
        try:
            write_api.write(bucket=self.bucket_name, org="ttu", record=record)
        except Exception as e:
            LOGGER.error(e)
