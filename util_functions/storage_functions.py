import logging
import fitz  # PyMuPDF
from docx import Document
from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage
import uuid
import zipfile

from services.sql_service import upload_files_metadata
from services.storage_service import upload_file
from util_functions.functions import get_module_session

def parseImagesFromFile(file_storage: FileStorage):
    """
    Parses images from a pdf or docx file and uploads them to the supabase storage if found.
    
    Parameters:
    - file_storage (FileStorage): The file to parse images from.
    
    Returns:
    - A list of the uploaded images.
    """
    file_type = file_storage.filename.split('.')[-1].lower()
    if file_type == 'pdf':
        return parseImagesFromPdf(file_storage)
    elif file_type == 'docx':
        return parseImagesFromDocx(file_storage)
    else:
        return None


def parseImagesFromPdf(file_storage: FileStorage):
    # Ensure the file pointer is at the beginning
    file_storage.seek(0)
    file_content = file_storage.read()
    
    if not file_content:
        logging.error("Error: The provided PDF file is empty.")
        return []

    try:
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
    except fitz.EmptyFileError:
        logging.error("Error: The provided PDF file cannot be opened.")
        return []

    images = []
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            img_name = f"{uuid.uuid4()}.{image_ext}"
            
            img_io = BytesIO(image_bytes)
            img_io.seek(0)
            image = Image.open(img_io)
            img_io = BytesIO()
            image.save(img_io, format=image.format)
            img_io.seek(0)
            file_storage = FileStorage(stream=img_io, filename=img_name, content_type=f"image/{image_ext}")
            images.append(file_storage)
    
    logging.info(f'Uploading images from PDF: {images}')
    return upload_images_to_supabase(images)

def parseImagesFromDocx(file_storage: FileStorage):
    # Ensure the file pointer is at the beginning
    file_storage.seek(0)
    file_content = file_storage.read()
    
    try:
        archive = zipfile.ZipFile(BytesIO(file_content))
    except zipfile.BadZipFile:
        print("Error: The provided file is not a valid DOCX file.")
        return []

    images = []
    
    for file in archive.filelist:
        if file.filename.startswith('word/media/') and file.file_size > 0:
            try:
                image_data = archive.read(file.filename)
                image_ext = file.filename.split('.')[-1]
                img_name = f"{uuid.uuid4()}.{image_ext}"
                
                img_io = BytesIO(image_data)
                img_io.seek(0)  # Ensure the pointer is at the start
                file_storage = FileStorage(stream=img_io, filename=img_name, content_type=f'image/{image_ext}')
                images.append(file_storage)
            except KeyError as e:
                print(f"Error accessing image part {file.filename}: {e}")
                
    logging.info(f'Uploading images from DOCX {images}')
    return upload_images_to_supabase(images)

def upload_images_to_supabase(file_storages: list[FileStorage]):
    uploaded_images = []
    
    module_session = get_module_session()
    
    for file_storage in file_storages:
        try:
            response = upload_file(bucket_name='images', file_storage=file_storage, folder='uploads', module_id=str(module_session['Id']))
            uploaded_images.append(response)
        except Exception as e:
            logging.error(f"Error uploading image: {e}")
            if not module_session or 'Id' not in module_session:
                return
            continue
    
    return uploaded_images

def upload_files_and_parse_images(bucket_name: str, file_storages: list[FileStorage], folder: str, module_id: str):
  """
  Uploads non-existent files to the Supabase storage and saves the metadata to the database.
  The method attempts to parse images from the uploaded files. If images are found, they are saved to the 'images' bucket, saving each image's
  metadata as well.
  
  Parameters:  
  - bucket_name (str): The name of the bucket.
  - file_storage (FileStorage): The file to be uploaded.
  - folder (str): The name of the folder to store the file in.
  - module_id (str): The ID of the module the file belongs to.
  
  Returns:
  uploaded_data, file_ids: A list of dictionaries containing the metadata of the uploaded files and the file ids.
  """
  #use one session
  file_ids = [str]
  uploaded_files = []
  if file_storages:
    sb_uploaded_files = []
    for file in file_storages:
      response = upload_file(bucket_name='documents', file_storage=file, folder='uploads', module_id=module_id)
      img_responses = parseImagesFromFile(file_storage=file)
      sb_uploaded_files.append(response)
    uploaded_files = upload_files_metadata(sb_uploaded_files, module_id)
    if uploaded_files:
      for file in uploaded_files:
        if 'Id' in file:
          file_ids.append(file['Id'])
    
    for img in img_responses:
      if 'error' in img:
        logging.error(f'Failed to upload parsed image {img}')
        continue
      logging.info(f'Uploaded parsed image {img}')
      
  return uploaded_files, file_ids