from flask import jsonify
from datetime import datetime
from bson import ObjectId
from db import mongo
from chat import extract_text_from_pdf
import random

def generate_unique_code():
    for _ in range(10):  # Try up to 10 times to generate a unique code
        code = str(random.randint(1000, 9999))
        exists = mongo.db.applications.find_one({"application_code": code})
        if not exists:
            return code
    raise Exception("Could not generate a unique 4-digit code")

def apply_to_job(candidate_id, job_id, cv_id):
    try:
        # Check if the candidate and CV exist
        cv = mongo.db.cvs.find_one({"_id": ObjectId(cv_id)})
        job = mongo.db.job_offers.find_one({"_id": ObjectId(job_id)})
        if not cv:
            return jsonify({"error": "CV not found"}), 404

        cv_path = cv.get("file_path")
        if not cv_path:
            return jsonify({"error": "CV path is missing"}), 500

        # Extract CV text
        cv_txt = extract_text_from_pdf(cv_path)
        if not cv_txt:
            return jsonify({"error": "Failed to extract text from CV"}), 500

        # Prevent duplicate application
        existing_application = mongo.db.applications.find_one({
            "candidate_id": ObjectId(candidate_id),
            "job_id": ObjectId(job_id),
            "cv_id": ObjectId(cv_id)
        })
        if existing_application:
            return jsonify({"error": "Candidate has already applied to this job with this CV"}), 409

        # Generate unique 4-digit code
        try:
            unique_code = generate_unique_code()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        # Application data with CV text and path
        application_data = {
            "candidate_id": ObjectId(candidate_id),
            "job_id": ObjectId(job_id),
            "cv_id": ObjectId(cv_id),
            "cv_text": cv_txt,
            "cv_path": cv_path,
            "applied_at": datetime.now(),
            "application_code": unique_code
        }

        # Insert application and return ID
        result = mongo.db.applications.insert_one(application_data)
        application_id = str(result.inserted_id)
        candidature = {
            "userId": candidate_id,
            "cv": cv,
            "job": job,
            "_id": application_id,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "cv_id": cv_id,
            "cv_text": cv_txt,
            "cv_path": cv_path,
            "applied_at": datetime.now(),
            "application_code": unique_code
        }
        return jsonify({
            "message": "Application submitted successfully",
            "candidature": candidature
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
def convert_objectid(doc):
    doc["_id"] = str(doc["_id"])
    if "candidate_id" in doc:
        doc["candidate_id"] = str(doc["candidate_id"])
    if "job_id" in doc:
        doc["job_id"] = str(doc["job_id"])
    if "cv_id" in doc:
        doc["cv_id"] = str(doc["cv_id"])
    return doc

def list_applications_by_candidate(candidate_id):
    try:
        applications_cursor = mongo.db.applications.find({
            "candidate_id": ObjectId(candidate_id)
        })
        applications = [convert_objectid(app) for app in applications_cursor]
        return jsonify(applications), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def list_applications_by_job(job_id):
    try:
        applications_cursor = mongo.db.applications.find({"job_id": ObjectId(job_id)})
        applications = [convert_objectid(app) for app in applications_cursor]
        return jsonify(applications), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def list_all_applications():
    try:
        applications_cursor = mongo.db.applications.find()
        applications = [convert_objectid(app) for app in applications_cursor]
        return jsonify(applications), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500