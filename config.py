import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here'
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'  # SQLite database for simplicity
    SQLALCHEMY_DATABASE_URI ='postgresql://admin:mypassword@db:5432/flask_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
