from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

bcrypt = Bcrypt()
jwt = JWTManager()

password = "HelloFriend"

password = bcrypt.generate_password_hash(password)

print(password)