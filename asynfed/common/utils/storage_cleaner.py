import os
import re
import logging

# logging.getlogging(__name__)
from asynfed.server.storage_connectors import ServerStorageBoto3


def delete_remote_files(cloud_storage: ServerStorageBoto3, folder_path: str, 
                        threshold: int = 0, best_version: int = None):
    files = cloud_storage.list_files(folder_path= folder_path)
    versions = [extract_model_version(folder_path= file) for file in files]
    delete_list = [file for file, version in zip(files, versions) if version <= threshold and version != best_version]


    if delete_list:
        logging.info("=" * 20)
        logging.info(f"Delete {len(delete_list)} files in remote folder: {folder_path}")
        logging.info(f"Threshold: {threshold}, best version: {best_version}")
        logging.info(f"version: {[extract_model_version(folder_path= file) for file in delete_list]}")
        logging.info("=" * 20)
        cloud_storage.delete_files(delete_list)



def delete_local_files(folder_path: str, threshold: int, best_version: int = None):
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    versions = [extract_model_version(folder_path= file) for file in files]
    delete_list = [file for file, version in zip(files, versions) if version <= threshold and version != best_version]

    if delete_list:
        logging.info("=" * 20)
        logging.info(f"Delete {len(delete_list)} files in local folder {folder_path}")
        logging.info([extract_model_version(folder_path= file) for file in delete_list])
        logging.info("=" * 20)

    for file in delete_list:
        full_path = os.path.join(folder_path, file)
        try:
            os.remove(full_path)
        except FileNotFoundError:
            logging.info(f"File {full_path} was not found")
        except PermissionError:
            logging.info(f"Permission denied for deleting {full_path}")
        except Exception as e:
            logging.info(f"Unable to delete {full_path} due to: {str(e)}")


# search for the pattern that
# an interger before a file extension
# it could be
# global-models/model-name/11234.pkl
# or
# 32432.pkl alone
def extract_model_version(folder_path: str) -> int:
    # Use os.path to split the path into components
    _, filename = os.path.split(folder_path)
    
    # Search for any sequence of digits (\d+) that comes directly before the file extension
    # match = re.search(rf'(\d+){re.escape(self.file_extension)}', filename)
    match = re.search(r'(\d+)\.', filename)  # Look for digits followed by a dot

    # If a match was found, convert it to int and return it
    if match:
        return int(match.group(1))
    
    # If no match was found, return None
    return None
