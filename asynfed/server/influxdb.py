from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

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
                print("Error: {}".format(e))

    def write_training_process_data(self, training_data):
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        measurement = training_data.client_id

        record = (
            Point(measurement)
            .field("client_id", training_data.client_id)
            .field("epoch", training_data.epoch)
            .field("train_acc", training_data.train_acc)
            .field("train_loss", training_data.train_loss)
            .time(training_data.timestamp, WritePrecision.NS)
        )
        write_api.write(bucket=self.bucket_name, org="ttu", record=record)
