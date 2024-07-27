from routes.users_routes import users_bp
from routes.document_routes import document_bp
from routes.openai_routes import openai_bp
from routes.agent_routes import agent_bp
from routes.auth_routes import auth_bp
from routes.module_routes import module_bp
from routes.history_routes import history_bp
from routes.utility_routes import utility_bp
def register_routes(app):
  """
  Registers the routes for the Flask application.

  Parameters:
      app (Flask): The Flask application instance.
  """
  app.register_blueprint(users_bp)
  app.register_blueprint(utility_bp)
  app.register_blueprint(module_bp)
  app.register_blueprint(history_bp)
  app.register_blueprint(document_bp)
  app.register_blueprint(openai_bp)
  app.register_blueprint(agent_bp)
  app.register_blueprint(auth_bp)
