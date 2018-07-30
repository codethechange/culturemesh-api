from flask import Blueprint, jsonify, g
from hashlib import md5
from flask_httpauth import HTTPBasicAuth
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)

from api.blueprints.users.utils import get_user_by_id, get_user_by_email, get_user_by_username
from api.credentials import secret_key
from api.config import AUTH_TOKEN_EXPIRATION_SECS
import time

accounts = Blueprint('account', __name__)

auth = HTTPBasicAuth()

"""
This Token Authentication approach draws heavy inspiration from
https://blog.miguelgrinberg.com/post/restful-authentication-with-flask
"""


@auth.verify_password
def verify_password(username_or_email_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_email_or_token)
    if not user:
        # try to authenticate with username/password
        user_obj = get_user_by_email(username_or_email_or_token)
        if user_obj is None:
            # username_or_email_or_token is likely a username.
            user_obj = get_user_by_username(username_or_email_or_token)
        if user_obj is not None:
            # Yay! we have a user! Let's convert it to a fancy User.
            user = User(user_obj)
            if not user.verify_password(password):
                return False
        else:
            return False
    else:
        user = User(user)
    g.user = user
    return True


@accounts.route('/token')
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return_dict = vars(g.user)
    return_dict['token'] = token.decode('ascii')
    return_dict['token_expiration_epoch'] = int(time.time()) + AUTH_TOKEN_EXPIRATION_SECS
    return jsonify(return_dict)


class User:
    """
    This user class is used by Flask Login to validate users.
    """
    def __init__(self, user_obj):
        """
        Instantiates user based on user_name and hashed password
        """
        self.id = user_obj['id']
        self.password_hash = user_obj['password']
        self.email = user_obj['email']
        self.username = user_obj['username']
        self.about_me = user_obj['about_me']
        self.first_name = user_obj['first_name']
        self.last_name = user_obj['last_name']
        self.role = user_obj['role']
        self.last_login = user_obj['last_login'] # TODO: possibly update this field?
        self.gender = user_obj['gender']
        self.img_link = user_obj['img_link']

    @staticmethod
    def hash_password(password):
        return md5(password.encode('utf-8')).hexdigest()

    def verify_password(self, password):
        return self.hash_password(password) == self.password_hash

    def generate_auth_token(self, expiration=AUTH_TOKEN_EXPIRATION_SECS):
        s = Serializer(secret_key, expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        return get_user_by_id(data["id"])

