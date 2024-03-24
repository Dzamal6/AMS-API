import os
import uuid
from services.sql_service import upload_files_metadata

def upload_files(files):
  files_with_ids = {
    str(uuid.uuid4()): file
    for file in files
  }

  responses = upload_files_metadata(files_with_ids)
  print(responses)

  directory_path = 'agent_files'
  if not os.path.exists(directory_path):
    os.makedirs(directory_path)

  for status, response in responses:
    if status == 'error' and 'Duplicate document found' in response.get('error', ''):
        print(f"Duplicate found, not saving file: {response.get('Id')}")
        continue

    file_id = response.get('Id')
    if file_id in files_with_ids:
        file = files_with_ids[file_id]
        new_file_path = os.path.join(directory_path, file_id)
        file.save(new_file_path)
        print(f"File saved: {new_file_path}")

  return responses