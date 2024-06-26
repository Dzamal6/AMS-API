import os
from itsdangerous import URLSafeSerializer
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI

# Database connection string
POSTGRES_CONNECTION_STRING = os.environ['POSTGRES_CONNECTION_STRING']

# Voiceflow API key for communication with the Voiceflow API
VOICEFLOW_KNOWLEDGE_BASE = 'https://api.voiceflow.com/v3alpha/knowledge-base/docs'
VOICEFLOW_ANALYTICS = 'https://analytics-api.voiceflow.com/v1/query/usage'
VOICEFLOW_TRANSCRIPTS = 'https://api.voiceflow.com/v2/transcripts'

FERNET_KEY = os.environ['FERNET_KEY'] # is used for encrypting & decrypting api tokens stored in db
SECRET_KEY = os.environ['SECRET_KEY']
LOGIN_KEY = os.environ['LOGIN_KEY']

# Encrypt and decrypt user cookie
user_session_serializer = URLSafeSerializer(LOGIN_KEY)
# Encrypt and decrypt assistant session cookie
assistant_session_serializer = URLSafeSerializer(SECRET_KEY)
# Encrypt and decrypt chat session cookie
chat_session_serializer = URLSafeSerializer(SECRET_KEY)

# OAI API key for communication with the OpenAI API
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# Initialize OAI client
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

# Initialize flask limiter
limiter = Limiter(key_func=get_remote_address)

# Declare allowed origins for CORS
ALLOWED_ORIGINS = ['https://127.0.0.1:5173', 'https://localhost:5173', os.environ['CLIENT_APP']]

# Configuring Google OAuth
GOOGLE_SECRET_KEY = 'your_secret_key'
GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']
