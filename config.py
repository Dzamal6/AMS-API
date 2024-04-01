import os
from itsdangerous import URLSafeSerializer
from pyairtable import Api
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI

POSTGRES_CONNECTION_STRING = os.environ['POSTGRES_CONNECTION_STRING']

VERSION_ID = os.environ['VERSION_ID']
DIALOG_API_KEY = os.environ['DIALOG_API_KEY']
PROJECT_API_KEY = os.environ['PROJECT_API_KEY']

VOICEFLOW_API_KEY = os.environ['VOICEFLOW_API_KEY']
VOICEFLOW_KNOWLEDGE_BASE = 'https://api.voiceflow.com/v3alpha/knowledge-base/docs'
VOICEFLOW_ANALYTICS = 'https://analytics-api.voiceflow.com/v1/query/usage'
VOICEFLOW_TRANSCRIPTS = 'https://api.voiceflow.com/v2/transcripts'

FERNET_KEY = os.environ['FERNET_KEY'] # is used for encrypting & decrypting api tokens stored in db
SECRET_KEY = os.environ['SECRET_KEY']
LOGIN_KEY = os.environ['LOGIN_KEY']

user_session_serializer = URLSafeSerializer(LOGIN_KEY)
assistant_session_serializer = URLSafeSerializer(SECRET_KEY)
chat_session_serializer = URLSafeSerializer(SECRET_KEY)

TA_INSTRUCTIONS = os.environ["TA_INS_SYSTEM"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

limiter = Limiter(key_func=get_remote_address)

ALLOWED_ORIGINS = ['https://127.0.0.1:5173', 'https://localhost:5173', os.environ['CLIENT_APP']]
