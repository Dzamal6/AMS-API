from flask import Blueprint, request, jsonify
from services.sql_service import get_all_files, delete_doc
import uuid
import os
import fitz  # PyMuPDF
from docx import Document
from services.document_service import upload_files

document_bp = Blueprint('documents', __name__)


@document_bp.route('/document/upload', methods=['POST'])
def upload_document():
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


@document_bp.route('/document/get_all', methods=['POST'])
def get_documents():
  files = get_all_files()
  if files is None:
    return jsonify({'error':
                    'An error occurred while retrieving documents.'}), 400

  return jsonify({"files": files}), 200


@document_bp.route('/document/delete', methods=['POST'])
def delete_document():
  file_id = request.json.get('document_id')

  deleted = delete_doc(file_id)
  if deleted is None:
    return jsonify({'error':
                    'An error occurred while deleting the document.'}), 400

  directory_path = 'agent_files'
  file_path = os.path.join(directory_path, file_id)

  if os.path.exists(file_path):
    os.remove(file_path)
    return jsonify({
        "message": "File deleted successfully.",
        'document_id': deleted
    }), 200
  else:
    return jsonify({'error': 'File not found'}), 404


@document_bp.route('/document/get_content', methods=['POST'])
def get_document_content():
  file_id = request.json.get('document_id')
  file_path = f'agent_files/{file_id}'

  if not os.path.exists(file_path):
    return jsonify({'error': 'File not found.'}), 404

  try:
    with open(file_path, 'r', encoding='utf-8') as file:
      content = file.read()
      # Perform a basic check for non-whitespace content
      if content.strip():
        return jsonify({"content": content}), 200
      else:
        return jsonify({'error': 'The document is empty.'}), 400
  except UnicodeDecodeError:
    print(f'Error decoding file: {file_path}')
    pass

  try:
    content = ""
    with fitz.open(file_path) as doc:
      for page in doc:
        content += page.get_text()
    if content:
      return jsonify({"content": content}), 200
  except Exception as e:
    print(f'An error occured: {e}')
    pass

  try:
    doc = Document(file_path)
    content = '\n'.join([para.text for para in doc.paragraphs])
    if content:
      return jsonify({"content": content}), 200
  except Exception as e:
    print(f'An error occured: {e}')
    pass

  return jsonify({'error': 'Unsupported file type or file is corrupt.'}), 400
