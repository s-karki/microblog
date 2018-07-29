from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler # enable email
import os

app = Flask(__name__)
app.config.from_object(Config) # set config from config object

db = SQLAlchemy(app)
migrate = Migrate(app, db) # makes migration easier
mail = Mail(app)

bootstrap = Bootstrap(app)

login = LoginManager(app)
login.login_view = 'login' # url_for('login'), view endpoint. If not logged in, redirect to login endpoint

from app import routes, models, errors # models are db models

if not app.debug:
    # email handler
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='Microblog Failure',
            credentials=auth, secure=secure)

        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler) # attach the mail handler

    # file handler
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=16384, backupCount=10)

    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO) # error severity DEBUG, INFO, WARNING, ERROR and CRITICAL
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Microblog startup")
