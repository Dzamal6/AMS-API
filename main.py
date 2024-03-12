from flask import Flask
from flask_cors import CORS
import config
from routes import routes
from services.session_service import check_session_validation
from database.database import engine, seed_data, upload_documents
from database.base import Base
import database.models
import logging

app = Flask(__name__)
CORS(app,
     supports_credentials=True,
     origins=config.ALLOWED_ORIGINS)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['LOGIN_KEY'] = config.LOGIN_KEY

config.limiter.init_app(app)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

# Base.metadata.create_all(engine)
# seed_data()
# upload_documents()

app.before_request(check_session_validation)

routes.register_routes(app)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=81)
