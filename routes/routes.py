from routes.users_routes import users_bp
from routes.project_routes import project_bp
from routes.knowledge_routes import knowledge_bp
from routes.transcript_routes import transcript_bp
from routes.voiceflow_routes import voiceflow_bp
from routes.document_routes import document_bp
from routes.openai_routes import openai_bp
def register_routes(app):
  app.register_blueprint(users_bp)
  app.register_blueprint(project_bp)
  app.register_blueprint(knowledge_bp)
  app.register_blueprint(transcript_bp)
  app.register_blueprint(voiceflow_bp)
  app.register_blueprint(document_bp)
  app.register_blueprint(openai_bp)
