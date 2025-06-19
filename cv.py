from flask import  url_for,jsonify,send_file
from werkzeug.utils import secure_filename
from bson import ObjectId
import os
import uuid
from datetime import datetime
from db import mongo

def add_cv(user_id, file, title, expertise, cv_txt, visibility='private'):


    # Validate inputs
    if not title or visibility not in ['public', 'private']:
        return {"error": "Invalid title or visibility"}, 400

    # Check if user exists
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return {"error": "User not found"}, 404

    # Validate file extension
    _, file_extension = os.path.splitext(secure_filename(file.filename))
    if file_extension.lower() != ".pdf":
        return {"error": "Only PDF files are allowed"}, 400

    # Save file
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    upload_folder = os.getenv('UPLOAD_CV_FOLDER', 'uploads/cvs')  # fallback folder
    filepath = upload_folder +"/" + unique_filename
    try:
        file.save(filepath)
    except Exception as e:
        return {"error": f"Failed to save file: {str(e)}"}, 500

    # Insert CV record
    cv_data = {
        "user_id": ObjectId(user_id),
        "title": title,
        "cv_txt": cv_txt,
        "expertise": expertise,
        "visibility": visibility,
        "file_path": filepath,
        "created_at": datetime.now()
    }
    mongo.db.cvs.insert_one(cv_data)

    return {"message": "CV uploaded successfully!"}, 201

def get_all_user_cvs(user_id):
    # Convert user_id to ObjectId if it’s not already
    user_id = ObjectId(user_id)

    # Fetch CVs from the cvs collection that belong to this user
    cvs_cursor = mongo.db.cvs.find({"user_id": user_id})

    # Convert the cursor to a list of dictionaries (and convert _id to string)
    cvs_list = []
    for cv in cvs_cursor:
        cv["_id"] = str(cv["_id"])
        cv["user_id"] = str(cv["user_id"])
        cvs_list.append(cv)

    return jsonify( cvs_list), 200

def update_user_cv(user_id, cv_id, data):
    user_id = ObjectId(user_id)
    cv_id = ObjectId(cv_id)

    # Fetch the CV document
    cv = mongo.db.cvs.find_one({"_id": cv_id, "user_id": user_id})
    if not cv:
        return jsonify({"error": "CV not found for this user"}), 404

    # Prepare updates
    updates = {}
    if "title" in data:
        updates["title"] = data["title"]
    if "visibility" in data:
        updates["visibility"] = data["visibility"]

    # Always update the 'updated_at' timestamp
    updates["updated_at"] = datetime.now()

    # Update only if there are changes
    if updates:
        mongo.db.cvs.update_one({"_id": cv_id}, {"$set": updates})

    return jsonify({"message": "CV updated successfully!"}), 200

def delete_user_cv(user_id, cv_id):
    user_id = ObjectId(user_id)
    cv_id = ObjectId(cv_id)

    # Check if the CV exists and belongs to the user
    cv = mongo.db.cvs.find_one({"_id": cv_id, "user_id": user_id})
    if not cv:
        return jsonify({"error": "CV not found for this user"}), 404

    # Delete the PDF file from the filesystem if it exists
    pdf_file_path = cv.get("file_path")
    if pdf_file_path and os.path.exists(pdf_file_path):
        try:
            os.remove(pdf_file_path)
        except Exception as e:
            return jsonify({"error": f"Failed to remove CV file: {str(e)}"}), 500

    # Delete the CV document
    mongo.db.cvs.delete_one({"_id": cv_id})

    return jsonify({"message": "CV deleted successfully!"}), 200

def get_all_public_cvs():
    cvs = list(mongo.db.cvs.find({"visibility": "public"}))
    for cv in cvs:
        cv["_id"] = str(cv["_id"])
        cv["user_id"] = str(cv["user_id"])
    return jsonify(cvs), 200


def search_public_cvs_logic(query):
    if not query:
        return {"msg": "Please provide a search query"}, 400

    cvs_cursor = mongo.db.cvs.find({
        "visibility": "public",
        "title": {"$regex": query, "$options": "i"}
    })

    cvs = []
    for cv in cvs_cursor:
        cv["_id"] = str(cv["_id"])
        cv["user_id"] = str(cv["user_id"])
        cvs.append(cv)

    return cvs, 200



def download_cv_logic(cv_id):

    cv = mongo.db.cvs.find_one({"_id": ObjectId(cv_id)})
    if not cv:
        return {"error": "CV not found"}, 404

    file_path = cv.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return {"error": "CV file not found"}, 404

    try:
        return send_file(file_path, as_attachment=True), 200
    except Exception as e:
        return {"error": f"Error sending file: {str(e)}"}, 500


def get_cv_file_path(cv_id):

    cv = mongo.db.cvs.find_one({"_id": ObjectId(cv_id)})

    if not cv  :
        return jsonify({"error": "CV not found for this user"}), 404

    return jsonify({"file_path": cv.get("file_path")}), 200

def get_cv_path(cv_id):
    cv = mongo.db.cvs.find_one({"_id": ObjectId(cv_id)})
    if not cv:
        return jsonify({"error": "CV not found"}), 404

    file_path = cv.get("file_path")
    if not file_path or not os.path.exists(file_path):  # optional file existence check
        return jsonify({"error": "File not found on server"}), 404

    return jsonify({
        "source": "http://127.0.0.1:5000/static/"+file_path ,  # convert to full URL
        "name": os.path.basename(file_path)
    }), 200


def get_cv_by_id(cv_id):
    try:
        cv = mongo.db.cvs.find_one({"_id": ObjectId(cv_id)})
    except Exception:
        return jsonify({"error": "Invalid CV ID format"}), 400

    if not cv:
        return jsonify({"error": "CV not found"}), 404
    
     # Fetch user info
    user = mongo.db.users.find_one({"_id": cv["user_id"]})
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Prepare response (convert ObjectId to string, exclude file path if not needed)
    result = {
        "_id": str(cv["_id"]),
        "title": cv.get("title", ""),
        "cv_txt": cv.get("title", ""),
        "expertise": cv.get("expertise", ""),
        "visibility": cv.get("visibility", "private"),
        "file_path": cv.get("file_path", None),
        "created_at": cv.get("created_at"),
        "user": {
            "_id": str(user["_id"]),
            "userName": user.get("userName", ""),
            "roles": user.get("roles", {})
        }
    }

    return jsonify(result), 200