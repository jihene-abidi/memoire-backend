from flask import request, jsonify, url_for,render_template
from werkzeug.security import generate_password_hash,check_password_hash # 1- pour chiffrer un mot de passe. # 2- pour comparer un mot de passe fourni avec celui stocké.
from flask_mail import Message # Pour envoyer des emails via Flask-Mail.
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature # Pour générer et valider des tokens sécurisés avec expiration 
from db import mongo, mail # Connexions à la base MongoDB et au service mail
import os # Pour charger les variables d’environnement depuis un fichier .env.
from dotenv import load_dotenv # Pour charger les variables d’environnement depuis un fichier .env.
from bson import ObjectId # Permet de manipuler les identifiants MongoDB
from datetime import datetime,timezone, timedelta
import jwt # Pour générer et décoder des JSON Web Tokens (JWT)
import uuid # Pour générer un identifiant unique
from werkzeug.utils import secure_filename # Pour sécuriser le nom d’un fichier uploadé
import random # Pour générer des nombres aléatoires


# Chargement des variables d'environnement à partir du fichier .env
load_dotenv()
# Initialisation du sérialiseur avec une clé secrète (pour la vérification d'email)
s = URLSafeTimedSerializer(os.getenv("EMAIL_TOKEN_SECRET"))


# Inscription utilisateur
def signup():
    data = request.json
    role = data.get("role")
    email = data.get("email")
    password = data.get("password")

    if not role or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    # Vérifie si l'utilisateur existe déjà
    if mongo.db.users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    # Hash du mot de passe
    hashed_pw = generate_password_hash(password)

    # Création d'un token de vérification
    token = s.dumps(email, salt='email-confirm')
    verification_link = url_for('verify_email', token=token, _external=True)

    # Insertion de l'utilisateur non vérifié dans la base
    mongo.db.users.insert_one({
        "role": role,
        "email": email,
        "password": hashed_pw,
        "is_verified": False
    })

    # Envoi de l'e-mail de vérification
    msg = Message('Verify Your Email', recipients=[email])
    msg.body = f'Hi , click the link to verify your email: {verification_link}'
    mail.send(msg)

    return jsonify({"message": "Signup successful! Check your email to verify your account."}), 201


# Vérification de l'adresse e-mail
def verify_email_token(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except (SignatureExpired, BadSignature):
        return jsonify({"error": "Invalid or expired token"}), 400

    user = mongo.db.users.find_one({"email": email})
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.get("is_verified"):
        return jsonify({"message": "Email already verified!"}), 200

    mongo.db.users.update_one({"email": email}, {"$set": {"is_verified": True}})
    return jsonify({"message": "Email verified successfully!"}), 200


# Mise à jour du profil utilisateur (nom, prénom, téléphone)
def update_user_profile(user_id, data):
    # On récupère uniquement les champs autorisés
    allowed_fields = {
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "phone": data.get("phone")
    }

    # Supprimer les champs non remplis
    clean_data = {k: v for k, v in allowed_fields.items() if v is not None}

    try:
        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": clean_data}
        )
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"message": "Profile updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


# Connexion utilisateur
def sign_in_user(data):
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'msg': 'Missing email or password'}), 400

    user = mongo.db.users.find_one({'email': email})
    if user and check_password_hash(user['password'], password):
        if user['is_verified']:
            token = jwt.encode({
                'user_id': str(user['_id']),
                'exp': datetime.now() + timedelta(hours=1)
            }, os.getenv('SECRET_KEY'), algorithm='HS256')

            return jsonify({'access_token': token}), 200
        else : 
            return jsonify({'msg': 'email pas verifier'}), 401
    else:
        return jsonify({'msg': 'Invalid email or password'}), 401



def update_profile_image(user_id, image):
    # Get user document
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Delete old image if exists
    old_image_path = user.get("profile_image")
    if old_image_path and os.path.exists(old_image_path):
        try:
            os.remove(old_image_path)
        except Exception as e:
            return jsonify({"error": f"Failed to remove old image: {str(e)}"}), 500

    # Generate a unique filename
    _, file_extension = os.path.splitext(secure_filename(image.filename))
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    relative_path = os.path.join('uploads', unique_filename)
    filepath = os.path.join(os.getenv('UPLOAD_FOLDER'), unique_filename)

    # Save new image
    image.save(filepath)

    # Update user document with new image path
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"profile_image": relative_path}}
    )

    return jsonify({
        "message": "Profile image updated successfully!",
    }), 200


def update_user_passwords(user_id, old_password, new_password):
    if not old_password or not new_password:
        return jsonify({"error": "Both old and new passwords are required"}), 400

    try:
        # Fetch the user from the database
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if the old password matches
        if not check_password_hash(user["password"], old_password):
            return jsonify({"error": "Old password is incorrect"}), 401

        # Hash the new password
        hashed_pw = generate_password_hash(new_password)

        # Update the password and the updated date
        update_data = {
            "password": hashed_pw,
            "updatedAt": datetime.now()
        }

        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )

        return jsonify({"message": "Password updated successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_user_by_email(email):
    user = mongo.db.users.find_one({"email": email})
    if user:
        return user["_id"], user["email"], user["password"], user.get("reset_code"), user.get("reset_code_expiration")
    return None

def update_user_reset_code(user_id, reset_code, reset_code_expires):
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "reset_code": reset_code,
            "reset_code_expiration": reset_code_expires
        }}
    )

def request_reset_password_logic():
    email = request.json.get('email')
    user = get_user_by_email(email)

    if user:
        user_id, user_email, user_password, user_reset_code, user_reset_code_expires = user

        reset_code = ''.join(random.choices('0123456789', k=6))
        reset_code_expires = datetime.now(timezone.utc) + timedelta(minutes=120)

        update_user_reset_code(user_id, reset_code, reset_code_expires)

        msg = Message('Password Reset Code', recipients=[email])
        msg.html = render_template('reset_password_email.html', reset_code=reset_code)
        mail.send(msg)

        return jsonify({"msg": "Password reset code sent to your email"}), 200

    return jsonify({"msg": "Email not found"}), 404



def update_user_password(user_id, new_hashed_password):
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {"password": new_hashed_password},
            "$unset": {"reset_code": "", "reset_code_expiration": ""}
        }
    )

def reset_password_logic():
    email = request.json.get("email")
    reset_code = request.json.get("reset_code")
    new_password = request.json.get("new_password")
    
    user = mongo.db.users.find_one({"email": email})
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.get("reset_code") != reset_code:
        return jsonify({"error": "Invalid reset code"}), 400

    if datetime.now() > user.get("reset_code_expiration"):
        return jsonify({"error": "Reset code has expired"}), 400

    hashed_pw = generate_password_hash(new_password)
    update_user_password(user["_id"], hashed_pw)

    return jsonify({"message": "Password reset successfully!"}), 200


def get_all_users():
    users = mongo.db.users.find()
    
    # Optionally hide sensitive info like password
    users_list = []
    for user in users:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string
        user.pop("password", None)      # Remove password
        users_list.append(user)

    return jsonify(users_list), 200

def get_user_by_id(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
            user.pop("password", None)  # Optional: remove sensitive data
            return jsonify(user), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Invalid user ID: {str(e)}"}), 400
    
def get_role_by_id(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404

        role = user.get("role")
        if not role:
            return jsonify({"error": "Role not assigned to user"}), 400

        return jsonify({"role": role}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500