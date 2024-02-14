import os
from itsdangerous import URLSafeSerializer
from pyairtable import Api

VERSION_ID = os.environ['VERSION_ID']
DIALOG_API_KEY = os.environ['DIALOG_API_KEY']
PROJECT_API_KEY = os.environ['PROJECT_API_KEY']

AIRTABLE_API_KEY = os.environ['AIRTABLE_API_KEY']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']
AIRTABLE_TABLE_NAME = os.environ['AIRTABLE_TABLE_NAME']
AIRTABLE_ENDPOINT = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'
HEADERS = {'Authorization': f"Bearer {AIRTABLE_API_KEY}"}

VOICEFLOW_API_KEY = os.environ['VOICEFLOW_API_KEY']
VOICEFLOW_KNOWLEDGE_BASE = 'https://api.voiceflow.com/v3alpha/knowledge-base/docs'
VOICEFLOW_ANALYTICS = 'https://analytics-api.voiceflow.com/v1/query/usage'
VOICEFLOW_TRANSCRIPTS = 'https://api.voiceflow.com/v2/transcripts'

FERNET_KEY = os.environ['FERNET_KEY'] # is used for encrypting & decrypting api tokens stored in db
SECRET_KEY = os.environ['SECRET_KEY']
LOGIN_KEY = os.environ['LOGIN_KEY']

user_session_serializer = URLSafeSerializer(LOGIN_KEY)
assistant_session_serializer = URLSafeSerializer(SECRET_KEY)

TA_INSTRUCTIONS = os.environ["TA_INS_SYSTEM"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

airtable_api = Api(AIRTABLE_API_KEY)
airtable_token_table = airtable_api.table('appS1lC4Fzpmre5cF', "tbl5kkyONHJFlOcNI")
airtable_user_table = airtable_api.table('appS1lC4Fzpmre5cF', 'tblTQJkH9Q6X77egQ')
airtable_points_table = airtable_api.table('appS1lC4Fzpmre5cF', 'tblNaHM7wEr5d3TTe')