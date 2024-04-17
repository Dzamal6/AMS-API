from routes.users_routes import users_bp
from routes.project_routes import project_bp
from routes.transcript_routes import transcript_bp
from routes.voiceflow_routes import voiceflow_bp
from routes.document_routes import document_bp
from routes.openai_routes import openai_bp
from routes.agent_routes import agent_bp
def register_routes(app):
  """
  Registers the routes for the Flask application.

  Parameters:
      app (Flask): The Flask application instance.
  """
  app.register_blueprint(users_bp)
  app.register_blueprint(project_bp)
  app.register_blueprint(transcript_bp)
  app.register_blueprint(voiceflow_bp)
  app.register_blueprint(document_bp)
  app.register_blueprint(openai_bp)
  app.register_blueprint(agent_bp)
