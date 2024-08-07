import logging
from flask import Blueprint, request, jsonify, send_file
from flask.helpers import make_response
from services.sql_service import get_all_files, delete_doc, get_file, upload_files, upload_files_metadata
import io
import uuid
import os
import fitz  # PyMuPDF
from docx import Document
from services.storage_service import delete_files, serve_file, upload_file
from util_functions.functions import roles_required, get_module_session
import mammoth

from util_functions.storage_functions import parseImagesFromFile

document_bp = Blueprint('documents', __name__)

@document_bp.route('/documents', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def upload_documents():
  """
  Uploads documents to the database and the Supabase storage

  URL:
  - POST /documents

  Parameters:
      files (list[FileStorage]): The files to be uploaded.

  Returns:
    JSON response (dict): Details of the uploaded documents along with a status message or an error message.

  Status Codes:
      200 OK: Document uploaded successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Requires one of the following roles: `Admin`, `Master`, `Worker`
  """
  module_session = get_module_session()

# TODO: CHECK EXISTS (HASH)
# TODO: ASSOCIATE FILES WITH IMAGE FILES (INTRODUCE FILE_ID TO EXTRACTED_IMAGES table IN DB)
  if module_session is None or not module_session:
    return jsonify({'error': 'Invalid module session.'}), 401
  
  module_id = str(module_session['Id'])

  files = request.files.getlist('files')
  if not files or any(file.filename == '' for file in files):
    return jsonify({'error': 'No file(s) provided'}), 400
  
  responses = []
  img_responses = []
  for file in files:
      response = upload_file(bucket_name='documents', file_storage=file, folder='uploads', module_id=module_id)
      img_responses = parseImagesFromFile(file_storage=file)
      responses.append(response)
      
  for img in img_responses:
    if 'error' in img:
      logging.error(f'Failed to upload parsed image {img}')
      continue
    logging.info(f'Uploaded parsed image {img}')
    
  if any('error' in response for response in responses):
    upload_files_metadata(files=responses, module_id=module_id)
    return jsonify({'error': 'Some or all files failed to upload.', 'responses': responses}), 400
  upload_metadata = upload_files_metadata(files=responses, module_id=module_id)

  if any('error' in response for response in upload_metadata):
    return jsonify({
        "message": "Some or all files failed to upload.",
        "details": upload_metadata
    }), 400
    
  return jsonify({'responses': upload_metadata}), 200

@document_bp.route('/documents', methods=['GET'])
@roles_required('admin', 'master', 'worker')
def get_documents():
  """
  Retrieves all documents metadata from the database.

  URL:
  - GET /documents

  Returns:
      JSON response (dict): A list of all documents or an error message.

  Status Codes:
      200 OK: Documents retrieved successfully.
      400 Bad Request: An error occurred.

  Access Control:
      Requires at least one of the following roles: `Admin`, `Master`, `Worker`.
      Requires an assistant to be set prior to its call.
  """
  module_session = get_module_session()
  if module_session is None or not module_session:
    return jsonify({'error': 'Invalid module session.'}), 401
  
  files = get_all_files(str(module_session['Id']))
  if files is None:
    return jsonify({'error':
                    'An error occurred while retrieving documents.'}), 400

  return jsonify({"files": files}), 200


@document_bp.route('/documents/document', methods=['GET'])
@roles_required('admin', 'master', 'worker')
def get_document():
  """
  Retrieves the content of a document based on its file ID. This function uses
  the `serve_file` method to fetch the document from the Supabase storage and then extracts
  the text using `PyMuPDF` or `docx` depending on the file type.

  URL:
  - GET /documents

  Parameters:
  - file_key (str): The Supabase storage URL of the document to retrieve.
  
  Note:
  - In order for this endpoint to function correctly, set the response type to 'blob' when receiving image files and pdfs
  and 'application/json' when receiving files like docx.

  Returns:
  - JSON response (dict): The retrieved document content or an error message.

  Status Codes:
  - 200 OK: Document content retrieved successfully.
  - 400 Bad Request: Invalid payload or an error occurred.

  Access Control:
  - Requires at least one of the following roles: `Admin`, `Master`, `Worker`
  """
  file_key = request.args.get('file_key')
  if not file_key:
    return jsonify({'error': 'Missing file key.'}), 400
  
  try:
    file_content = serve_file(file_key=file_key)
    if file_content is None:
      return jsonify({'error': 'File not found.'}), 404
    
    if file_key.endswith('.docx') or file_key.endswith('.doc'):
      with file_content:
        result = mammoth.convert_to_html(file_content)
        response = make_response(jsonify({'content': result.value, 'type': 'html'}))
        return response
    
    return send_file(file_content, as_attachment=True, download_name=file_key)
  except Exception as e:
    logging.error(f'Failed to serve file {file_key} because {e}')
    return jsonify({'error': f'Failed to serve file {file_key}. {e}'}), 400
  
  
@document_bp.route('/documents', methods=['DELETE'])
@roles_required('admin', 'master', 'worker')
def destroy_document():
  """
  Deletes a document from the database using the specified file ID. The file is also deleted from the Supabase storage.

  URL:
  - DELETE /documents

  Parameters:
      file_id (str): The database ID of the document to be deleted.

  Returns:
      JSON response (dict): A message indicating the deletion status along with details of the deleted document or an error message.

  Status Codes:
      200 OK: Document deleted successfully.
      400 Bad Request: An error occurred.

  Access Control:
      Requires at least one of the following roles: `Admin`, `Master`, `Worker`
  """
  file_id = request.args.get('file_id')
  module_session = get_module_session()

  if module_session is None or not module_session:
    return jsonify({'error': 'Invalid module session.'}), 401
  
  module_id = str(module_session['Id'])
  docId, file_key = delete_doc(file_id, module_id=module_id)
  if docId is None:
    return jsonify({'error':
                    'An error occurred while deleting the file.'}), 400
    
  sb_delete, status = delete_files(file_keys=[file_key])
  
  if status == True:
    return jsonify({
      "message": "File deleted successfully.",
      'document_id': docId
  }), 200
  else:
    return jsonify({'error': f'Failed to delete some or all files! {sb_delete}'}), 400
  
### OLD DEPRECATED CODE 
#  I
#  I
# \/
  
@document_bp.route('/document/upload', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def upload_document():
  """
  Uploads one or more documents to the database.

  URL:
  - POST /document/upload

  Parameters:
      files (list of FileStorage): The files to be uploaded.

  Returns:
      JSON response (dict): Details of the uploaded documents along with a status message or an error message.

  Status Codes:
      200 OK: Document uploaded successfully.
      400 Bad Request: Invalid request payload or an error occurred.

  Access Control:
      Requires one of the following roles: `Admin`, `Master`, `Worker`
  """
  module_session = get_module_session()

  if module_session is None or not module_session:
    return jsonify({'error': 'Invalid module session.'}), 401
  
  module_id = str(module_session['Id'])

  files = request.files.getlist('file')
  if not files or any(file.filename == '' for file in files):
    return jsonify({'error': 'No file(s) provided'}), 400

  module_ids = []
  module_ids.append(module_id)
  responses = upload_files(files, module_ids)

  stripped_responses = []
  for status, response in responses:
      response.pop('status', None)
      response.pop('error', None)
      stripped_responses.append(response)

  if any(status == 'error' for status, response in responses):
    return jsonify({
        "message": "Some or all files failed to upload.",
        "details": stripped_responses
    }), 400

  return jsonify({"message": "Upload successful.", "details": stripped_responses}), 200


@document_bp.route('/document/delete', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def delete_document():
  """
  Deletes a document from the database using the specified file ID.

  URL:
  - POST /document/delete

  Parameters:
      file_id (str): The ID of the document to be deleted.

  Returns:
      JSON response (dict): A message indicating the deletion status along with details of the deleted document or an error message.

  Status Codes:
      200 OK: Document deleted successfully.
      400 Bad Request: An error occurred.

  Access Control:
      Requires at least one of the following roles: `Admin`, `Master`, `Worker`
  """
  file_id = request.json.get('document_id')
  module_session = get_module_session()

  if module_session is None or not module_session:
    return jsonify({'error': 'Invalid module session.'}), 401
  
  module_id = str(module_session['Id'])
  deleted = delete_doc(file_id, module_id=module_id)
  if deleted is None:
    return jsonify({'error':
                    'An error occurred while deleting the document.'}), 400

  return jsonify({
      "message": "File deleted successfully.",
      'document_id': deleted
  }), 200



@document_bp.route('/document/get_content', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def get_document_content():
  """
  Retrieves the content of a document based on its file ID. This function uses
  the `get_file` method to fetch the document from the database and then extracts
  the text using `PyMuPDF` or `docx` depending on the file type.

  URL:
  - POST /document/get_content

  Parameters:
      file_id (str): The ID of the document to retrieve.

  Returns:
      JSON response (dict): The retrieved document content in plain text or an error message.

  Status Codes:
      200 OK: Document content retrieved successfully.
      400 Bad Request: Invalid payload or an error occurred.

  Access Control:
      Requires at least one of the following roles: `Admin`, `Master`, `Worker`
  """
  file_id = request.json.get('document_id')
  file = get_file(file_id)

  if file is None:
    return jsonify({'error': 'Failed to retrieve file content.'}), 400

  file_content_bytes = file['Content']
  if not isinstance(file_content_bytes, bytes):
      return jsonify({'error': 'File content is not in the correct format.'}), 400

  try:
    text_content = file_content_bytes.decode('utf-8')
    if text_content.strip():
        return jsonify({"content": text_content}), 200
  except UnicodeDecodeError:
    pass

  try:
    with fitz.open(stream=file_content_bytes, filetype="pdf") as doc:
        content = ""
        for page in doc:
            content += page.get_text()
        if content:
            return jsonify({"content": content}), 200
  except RuntimeError:
    pass

  try:
    doc = Document(io.BytesIO(file_content_bytes))
    content = '\n'.join([para.text for para in doc.paragraphs])
    if content:
        return jsonify({"content": content}), 200
  except ValueError:
    pass

  return jsonify({'error': 'File format not supported or the document is empty.'}), 400

  
