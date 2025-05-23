from flask import Flask, redirect, url_for
from medical_log.backend import medical_log_bp
from translator import translator_bp

def create_app():
    app = Flask(__name__)
    # app.config.from_pyfile('config.py')

    # Register Blueprints
    app.register_blueprint(medical_log_bp, url_prefix='/medical_log')
    app.register_blueprint(translator_bp, url_prefix='/translator')
    # app.register_blueprint(api_bp, url_prefix='/api')

    # Define routes
    # @app.route("/")
    # def home():
    #     return redirect(url_for('medical_log.index'))  # Use blueprint_name.view_function_name

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
