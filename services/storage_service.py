from io import BytesIO
import json
import logging
from werkzeug.datastructures.file_storage import FileStorage
from config import SB_CLIENT
from util_functions.functions import normalize_file_name
from supabase import StorageException

def upload_file(bucket_name: str, file_storage: FileStorage, folder: str, module_id: str):
    """
    Uploads a file to a specified bucket in Supabase storage.

    Parameters:
    - bucket_name (str): The name of the bucket.
    - file_storage (FileStorage): The file to be uploaded.
    - folder (str): The name of the folder to store the file in.
    - module_id (str): The ID of the module the file belongs to.
    
    Returns:
    - dict[str, any]: The `Id`, `URL`, `Name`, `ModuleID` and `FileType` of the uploaded file.
    """
    try:
        storage_path = f'{folder}/{module_id}/{normalize_file_name(file_storage.filename)}'
        fileType = file_storage.filename.split('.')[-1]
        file_content = file_storage.read()
        response = SB_CLIENT.storage.from_(bucket_name).upload(storage_path, file_content)
        response = response.json()
        
        logging.info(f"File uploaded successfully: {response.get('Key')}")
        return {'Id': response.get('Id'), 'URL': response.get('Key'), 'Name': file_storage.filename, 'ModuleID': str(module_id), 'FileType': fileType}
    except Exception as e:
        logging.error(f"Failed to upload file due to an unexpected error! {e}")
        
        # Attempt to parse the error message as JSON
        try:
            error_message = str(e).replace("'", '"')
            error_details = json.loads(error_message)
            if error_details['error'] == 'Duplicate':
                return {'Name': file_storage.filename, 'URL': f'{bucket_name}/{storage_path}', 'FileType': fileType, 'ModuleID': str(module_id)}
            return {'error': error_details.get('error', 'Unknown error'), 'message': error_details.get('message', 'No message'), 'file_path': storage_path}
        except json.JSONDecodeError as je:
            logging.error(f'Failed to parse error. {je}')
            return {'error': f'Failed to upload file due to an unexpected error.', 'file_path': storage_path}

    
def serve_file(file_key: str):
    """
    Downloads a file from the Supabase storage based on the specified file key.

    Parameters:
    - file_key (str): The key used to retrieve the file data from the storage.

    Returns:
    - str: The file's content type.
    """
    try:
        bucket_name = file_key.split('/')[0]
        file_key = file_key.replace(f'{bucket_name}/', '')
        response = SB_CLIENT.storage.from_(bucket_name).download(file_key)
        if response:
            file_content = BytesIO(response)
            return file_content
        else:
            logging.error(f"Error downloading file: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Failed to download file! {e}")
        return None
    
def delete_files(file_keys: list[str]):
    """
    Deletes files from the Supabase storage based on the file keys.
    
    Parameters:
    - file_keys (list[str]): List of keys used to delete the files from the storage.
    
    Returns:
    - list[str], bool: The list of deleted file keys if the operation was successful. An empty list otherwise. A bool indicator of whether the operation was successful is also returned.
    """
    deleted_files = []
    try:
        for file_key in file_keys:
            bucket_name = file_key.split('/')[0]
            file_path = file_key.replace(f'{bucket_name}/', '')
            response = SB_CLIENT.storage.from_(bucket_name).remove([file_path])
            if response:
                deleted_files.append(file_key)
        
        return deleted_files, True if deleted_files else False
    except Exception as e:
        logging.error(f"Failed to delete some or all files! {e}")
        return deleted_files, False