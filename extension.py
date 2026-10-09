from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
bcrypt = Bcrypt()
jwt = JWTManager()
cors = CORS()
oauth = OAuth()

# password = "HelloFriend"

# password = bcrypt.generate_password_hash(password)

# print(password)