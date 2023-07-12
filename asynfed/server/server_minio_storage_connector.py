import logging
from asynfed.commons.utils import MinioConnector

LOGGER = logging.getLogger(__name__)


class ServerStorageMinio(MinioConnector):
    def __init__(self, minio_config):
        super().__init__(minio_config)
        self.create_bucket()
        self.client_access_key = minio_config['client_access_key']
        self.client_secret_key = minio_config['client_secret_key']

    def create_bucket(self):
        try:
            logging.info(f"Creating bucket {self.bucket_name}")
            # print(f"Creating bucket {self.bucket_name}")
            self._s3.create_bucket(
                Bucket=self.bucket_name,
                # CreateBucketConfiguration={'LocationConstraint': minio_config['region_name']}
            )            
            logging.info(f"Created bucket {self.bucket_name}")
            # print(f"Created bucket {self.bucket_name}")
            self._s3.put_object(Bucket=self.bucket_name, Key='global-models/')

        except Exception as e:
            if 'BucketAlreadyOwnedByYou' in str(e):
                logging.info(f"Bucket {self.bucket_name} already exists")
                # print(f"Bucket {self.bucket_name} already exists")
            else:
                logging.error(e)
                # print(e)

    def get_client_key(self, worker_id):
        self.create_folder(worker_id)
        return self.client_access_key, self.client_secret_key

    def create_folder(self, folder_name):
        self._s3.put_object(Bucket=self.bucket_name, Key=('clients/' + folder_name + '/'))

    def get_newest_global_model(self) -> str:
        # get the newest object in the global-models bucket
        objects = self._s3.list_objects_v2(Bucket=self.bucket_name, Prefix='global-models/', Delimiter='/')['Contents']
        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)

        try:
            if sorted_objects[0]['Key'] == 'global-models/':
                LOGGER.info(sorted_objects)
                return sorted_objects[1]['Key']
            return sorted_objects[0]['Key']
        except:
            LOGGER.info("*" * 20)
            LOGGER.info("NO MODEL EXIST YET")
            LOGGER.info("Uploading initial model...")
            self.upload('./testweight_v1.pkl', 'global-models/testweight_v1.pkl')
            LOGGER.info("Upload initial model succesfully")
            LOGGER.info("*" * 20)
            return 'global-models/testweight_v1.pkl'

    def delete_bucket(self):
        try:
            self._s3.delete_bucket(Bucket=self.bucket_name)
            logging.info(f'Success! Bucket {self.bucket_name} deleted.')
        except Exception as e:
            logging.error(f'Error! Bucket {self.bucket_name} was not deleted. {e}')