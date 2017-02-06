from flask import Flask, render_template

from api import api
from auth import auth
from db import models

app = Flask(__name__)
app.config.from_pyfile('app.conf')
# db init
db = models.db
db.init_app(app)
# init API
app.register_blueprint(api.api)
# auth init
auth.init_app(app)
app.register_blueprint(auth.auth, url_prefix='/auth')


@app.route('/')
@app.route('/login', methods=['GET'])
@app.route('/register', methods=['GET'])
@app.route('/logout', methods=['GET'])
def home():
    return render_template('index.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(port=10000)
