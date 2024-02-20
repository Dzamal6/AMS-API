from flask import Flask
from flask_cors import CORS
import config
from routes import routes
from services.session_service import check_session_validation
from database.database import engine, seed_data
from database.base import Base
import database.models
import logging

app = Flask(__name__)
CORS(app,
     supports_credentials=True,
     origins=['https://127.0.0.1:5173', 'https://localhost:5173', 'https://partners-client.vercel.app'])
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['LOGIN_KEY'] = config.LOGIN_KEY

config.limiter.init_app(app)

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
Base.metadata.create_all(engine)
seed_data()

app.before_request(check_session_validation)

routes.register_routes(app)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=81)
