from flask import Blueprint, request, jsonify, send_file
from services.sql_service import get_all_files, delete_doc, get_file, upload_files
import io
import uuid
import os
import fitz  # PyMuPDF
from docx import Document

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

  return jsonify({
      "message": "File deleted successfully.",
      'document_id': deleted
  }), 200



@document_bp.route('/document/get_content', methods=['POST'])
def get_document_content():
  file_id = request.json.get('document_id')
  file = get_file(file_id)

  if file is None:
    return jsonify({'error': 'Failed to retrieve file content.'}), 400

  file_content_bytes = file['Content']
  if not isinstance(file_content_bytes, bytes):
      return jsonify({'error': 'File content is not in the correct format.'}), 500

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

  
