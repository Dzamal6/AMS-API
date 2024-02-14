from flask import Flask
from flask_cors import CORS
import config
from routes import routes
from services.session_service import check_session_validation

app = Flask(__name__)
CORS(app,
     supports_credentials=True,
     origins=['https://127.0.0.1:5173', 'https://localhost:5173', 'https://partners-client.vercel.app'])
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['LOGIN_KEY'] = config.LOGIN_KEY

app.before_request(check_session_validation)

routes.register_routes(app)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=81)
