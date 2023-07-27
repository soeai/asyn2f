
import os
import re 
import logging


class StorageCleaner(object):
    def __init__(self, global_model_folder: str, local_model_folder: str):
        self.global_model_folder = global_model_folder
        self.local_model_folder = local_model_folder

    def delete_local_files(self, is_global_folder: bool, 
                           threshold: int, best_version: int = None):
        if is_global_folder:
            folder_path = self.global_model_folder
        else:
            folder_path = self.local_model_folder

        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        versions = [self.extract_model_version(folder_path= file) for file in files]
        delete_list = [file for file, version in zip(files, versions) if version <= threshold and version != best_version]

        if delete_list:
            logging.info("=" * 20)
            logging.info(f"Delete {len(delete_list)} files in local folder {folder_path}")
            logging.info([self.extract_model_version(folder_path= file) for file in delete_list])
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


    def extract_model_version(self, folder_path: str) -> int:
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

