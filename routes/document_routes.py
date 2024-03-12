from flask import Blueprint
from flask import request
from flask.json import jsonify
from services.sql_service import upload_docs, get_docs, delete_doc

document_bp = Blueprint('documents', __name__)

@document_bp.route('/document/upload', methods=['POST'])
def upload_document():
  file = request.files['file']
  upload_docs(file)
  return jsonify({"message": "Upload succesful."}), 200

@document_bp.route('/document/get', methods=['POST'])
def get_documents():
  return jsonify({"docs": get_docs()}), 200

@document_bp.route('/document/delete', methods=['POST'])
def delete_document():
  docId = request.json.get('docId')
  return jsonify({delete_doc(docId)}), 200