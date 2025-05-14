from flask import jsonify,request
from datetime import datetime
from db import mongo
from bson import ObjectId
import re


def create_job_offers(job_data):
    job_offer = {
        "title": job_data.get("title"),
        "company": job_data.get("company"),
        "location": job_data.get("location"),
        "technologies": job_data.get("technologies", []),
        "skills": job_data.get("skills", []),
        "published_on": job_data.get("published_on", datetime.now()),
        "job_description": job_data.get("job_description"),
        "salary": job_data.get("salary"),
        "contract_duration": job_data.get("contract_duration"),
        "start_date": job_data.get("start_date")
    }

    try:
        mongo.db.job_offers.insert_one(job_offer)
        return jsonify({"message": "Job offer created successfully"}), 201
    except Exception as e:
        return jsonify({"message": "Failed to create job offer", "error": str(e)}), 500


def delete_job_offer_by_id(job_id):
    result = mongo.db.job_offers.delete_one({"_id": ObjectId(job_id)})
    
    if result.deleted_count == 1:
        return jsonify({"msg": f"Job offer {job_id} deleted successfully."}), 200
    else:
        return jsonify({"error": "Job offer not found."}), 404
    
# Function to convert ObjectId to string
def convert_objectid(job):
    job["_id"] = str(job["_id"])
    return job

# Function to list all job offers
def list_all_job_offers():
    try:
        job_offers_cursor = mongo.db.job_offers.find()
        job_offers = [convert_objectid(job) for job in job_offers_cursor]
        return jsonify(job_offers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def get_job_offer_by_id(job_id):
    try:
        job_offer = mongo.db.job_offers.find_one({"_id": ObjectId(job_id)})
        
        if not job_offer:
            return jsonify({"error": "Job offer not found"}), 404

        job_offer["_id"] = str(job_offer["_id"])  # Convert ObjectId to string
        return jsonify(job_offer), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def update_job_offer_by_id(job_id, update_data):
    if not update_data:
        return jsonify({"error": "No data provided for update"}), 400

    try:
        result = mongo.db.job_offers.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Job offer not found"}), 404

        return jsonify({"message": f"Job offer {job_id} updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500





def search_job_offers():
    try:
        keyword = request.args.get('keyword', '')
        if not keyword:
            return jsonify({"error": "No keyword provided"}), 400

        # Case-insensitive search across relevant fields
        query = {
            "$or": [
                {"title": {"$regex": re.escape(keyword), "$options": "i"}},
                {"company": {"$regex": re.escape(keyword), "$options": "i"}},
                {"location": {"$regex": re.escape(keyword), "$options": "i"}},
                {"technologies": {"$regex": re.escape(keyword), "$options": "i"}},
                {"skills": {"$regex": re.escape(keyword), "$options": "i"}}
            ]
        }

        results = mongo.db.job_offers.find(query)
        job_offers = []
        for job in results:
            job["_id"] = str(job["_id"])
            job_offers.append(job)

        return jsonify(job_offers), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
