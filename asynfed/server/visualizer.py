import os
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import dotenv

dotenv.load_dotenv()


class Visualizer():
    def __init__(self, url, token, org, bucket_name, test=True):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.test = test
        self.bucket_name = bucket_name

        self._create_bucket(bucket_name)

    def _create_bucket(self, bucket_name):
        try:
            bucket_api = self.client.buckets_api()
            bucket_api.create_bucket(bucket_name=bucket_name)
        except Exception as e:
            if 'already exists' in e.message:
                pass
            else:
                raise e

    def write_training_process_data(self, training_data):
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        measurement = training_data.client_id

        point = (
            Point(measurement)
            .field("client_id", training_data.client_id)
            .field("epoch", training_data.epoch)
            .field("dataset_size", training_data.dataset_size)
            .field("batch_size", training_data.batch_size)
            .field("current_batch_num", training_data.current_batch_num)
            .field("train_acc", training_data.train_acc)
            .field("train_loss", training_data.train_loss)
            .time(training_data.timestamp, WritePrecision.NS)
        )
        write_api.write(bucket=self.bucket_name, org="ttu", record=point)


if __name__ == '__main__':
    url = os.getenv('INFLUXDB_URL')
    token = os.getenv('INFLUXDB_TOKEN')
    org = os.getenv('INFLUXDB_ORG')
    bucket = os.getenv('INFLUXDB_BUCKET')

    viz = Visualizer(url, token, org, bucket, test=True)
    training_data = {'timestamp': '2023-06-14 03:42:04', 'client_id': 'client1', 'epoch': 2, 'dataset_size': 100, 'batch_size': 10, 'current_batch_num': 5, 'train_acc': 0.92, 'train_loss': 0.09}
    # viz.write_training_process_data(training_data)

