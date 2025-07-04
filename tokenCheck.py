
import os
import bcrypt
import jwt
from dotenv import load_dotenv
from functools import wraps
from flask import Flask, request, jsonify
load_dotenv()

SECRET_KEY =os.getenv("SECRET_KEY")
from functools import wraps
from flask import request, jsonify
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 1️⃣ Try Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # 2️⃣ Fallback to cookie 'admin_token'
        if not token:
            token = request.cookies.get("admin_token")

        # 3️⃣ Fallback to cookie 'token'
        if not token:
            token = request.cookies.get("token")

        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            decoded_data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return f(decoded_data, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

    return decorated
