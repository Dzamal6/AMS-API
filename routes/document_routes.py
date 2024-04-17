from flask import Blueprint, request, jsonify, send_file
from services.sql_service import get_all_files, delete_doc, get_file, upload_files
import io
import uuid
import os
import fitz  # PyMuPDF
from docx import Document
from functions import roles_required

document_bp = Blueprint('documents', __name__)


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
  files = request.files.getlist('file')
  if not files or any(file.filename == '' for file in files):
    return jsonify({'error': 'No file(s) provided'}), 400

  responses = upload_files(files)

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

# TODO: Retrieve only documents associated with current assistant_session assistant
#       Endpoint should be GET (change will break frontend)
@document_bp.route('/document/get_all', methods=['POST'])
@roles_required('admin', 'master', 'worker')
def get_documents():
  """
  Retrieves all documents from the database.

  URL:
  - POST /document/get_all

  Returns:
      JSON response (dict): A list of all documents or an error message.

  Status Codes:
      200 OK: Documents retrieved successfully.
      400 Bad Request: An error occurred.

  Access Control:
      Requires at least one of the following roles: `Admin`, `Master`, `Worker`
  """
  files = get_all_files()
  if files is None:
    return jsonify({'error':
                    'An error occurred while retrieving documents.'}), 400

  return jsonify({"files": files}), 200


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

  deleted = delete_doc(file_id)
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

  
