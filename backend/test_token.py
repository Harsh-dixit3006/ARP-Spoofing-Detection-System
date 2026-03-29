import jwt
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key")

token = jwt.encode({
    "id": "60d5ecb8b392d715",
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
}, JWT_SECRET, algorithm="HS256")

print(token)