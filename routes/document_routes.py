from flask import Blueprint
from flask import request
from services.sql_service import upload_docs

document_bp = Blueprint('documents', __name__)

@document_bp.route('/document/upload', methods=['POST'])
def upload_document():
  file = request.files['file']
  upload_docs(file)
  return "ass"