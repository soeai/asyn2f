from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import csv
import os
from datetime import datetime
import dotenv
dotenv.load_dotenv()

def write(measurement):
    # InfluxDB connection settings
    url = os.getenv('INFLUXDB_URL')
    token = os.getenv('INFLUXDB_TOKEN')
    org = os.getenv('INFLUXDB_ORG')
    bucket = os.getenv('INFLUXDB_BUCKET')

    client = InfluxDBClient(url=url, token=token, org=org)
    buckets_api = client.buckets_api()
    try:
        buckets_api.find_bucket_by_name(bucket)
    except:
        buckets_api.create_bucket(bucket_name=bucket)

    # Open the CSV file for reading
    csv_file = 'output.csv'
    write_api = client.write_api(write_options=SYNCHRONOUS)
    with open(csv_file, 'r') as file:
        # Create a CSV reader object
        reader = csv.reader(file)
        headers = next(reader)
        data_points = []

        for row in reader:
            time_now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            record = (
                Point(measurement)
                .tag(headers[1], row[1])
                .field(headers[2], float(row[2]))
                .field(headers[3], float(row[3]))
                .time(row[0], WritePrecision.NS))
            try:
                data_points.append(record)
                # write_api.write(bucket=bucket, org=org, record=record)
                # print(f'wrote {row[0]} to influxdb')
            except Exception as e:
                raise e

    write_api.write(bucket=bucket, org=org, record=data_points)
    print(f'Wrote {len(data_points)} records to influxdb, bucket: {bucket}, measurement: {measurement}')

            # data_point = Point(measurement)
            # for i, value in enumerate(row):
            #     field_name = headers[i]
            #     try:
            #         data_point.field(field_name, float(value))
            #     except ValueError:
            #         pass
            # data_points.append(data_point)

    # Create an InfluxDB client instance

    # Create the write API instance and write line protocol data
    # write_api.write(bucket=bucket, org=org, record=data_points, write_precision=WritePrecision.NS)


if __name__ == '__main__':
    import log2csv
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file', help='Input log file', default='server.log')
    parser.add_argument('--measurement', type=str, default='mea2')
    args = parser.parse_args()

    log2csv.to_csv(args.input_file, 'output.csv')
    write(args.measurement)

