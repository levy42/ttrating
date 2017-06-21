from flask import Flask
from flask import request
from flask import Response

app = Flask(__name__)

@app.before_request
def auth():
    def check_auth(username, password):
        return username == 'admin' and password == 'secret'

    def authenticate():
        return Response('Login Required', 401,
                        {'WWW-Authenticate': 'Basic realm="Login Required"'})

    _auth = request.authorization
    if not _auth or not check_auth(_auth.username, _auth.password):
        return authenticate()


@app.route('/')
def home():
    return 'Hello World'

app.run()
