from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from db import mongo,mail
from job import create_job_offers,delete_job_offer_by_id,list_all_job_offers,get_jobs_by_user,create_job_offer_from_linkedin_url,update_job_offer_by_id,get_job_offer_by_id,search_job_offers
from users import signup,verify_email_token,update_user_profile,sign_in_user,update_profile_image,request_reset_password_logic,reset_password_logic,get_all_users,get_user_by_id,get_role_by_id,update_user_passwords
from flask_cors import CORS
import json
from flask import send_from_directory
from cv import get_all_user_cvs, add_cv, update_user_cv, delete_user_cv, get_all_public_cvs, search_public_cvs_logic, download_cv_logic, get_cv_file_path, get_cv_path,get_cv_by_id
from chat import extract_text_from_pdf, get_cv_chat_response, extract_text_from_pdf,analyze_cv_text, analyze_cv_text_skills
from apply import apply_to_job,list_applications_by_candidate,list_applications_by_job,list_all_applications
from interview import start_interview_process,interview_sessions,handle_answer_process,get_conversation_data
from evaluation_report import generate_candidate_report
from bson import ObjectId

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)
# Load Mail Config from .env
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config["MONGO_URI"] = os.getenv("MONGO_URI")

mongo.init_app(app)
mail.init_app(app)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(os.getenv('UPLOAD_FOLDER'), filename)

@app.route('/signup', methods=['POST'])
def user_signup():
    return signup()


@app.route('/verify/<token>')
def verify_email(token):
    return verify_email_token(token)


@app.route('/update-profile/<user_id>', methods=['PUT'])
def update_profile(user_id):
    data = request.json
    return update_user_profile(user_id, data)


@app.route('/sign-in', methods=['POST'])
def sign_in():
    data = request.json
    return sign_in_user(data)



@app.route('/update-profile-image/<user_id>', methods=['POST'])
def update_profile_image_route(user_id):
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image = request.files['image']
    if image.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    return update_profile_image(user_id, image)  # Call the function from the controller


@app.route('/request-reset-password', methods=['POST'])
def request_reset_password():   
    return request_reset_password_logic()


@app.route('/reset-password', methods=['POST'])
def reset_password():
    return reset_password_logic()

@app.route("/update-password/<user_id>", methods=["POST"])
def update_password(user_id):
    data = request.json
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    return update_user_passwords(user_id, old_password, new_password)

@app.route('/users', methods=['GET'])
def list_users():
    return get_all_users()

@app.route('/users/<user_id>', methods=['GET'])
def fetch_user(user_id):
    return get_user_by_id(user_id)

@app.route('/roles/<user_id>', methods=['GET'])
def fetch_role(user_id):
    return get_role_by_id(user_id)

# Access the job_offers collection
job_offers = mongo.db.job_offers



@app.route('/create-job-offer', methods=['POST'])
def create_job_offer():
    job_data = request.json
    return create_job_offers(job_data)


@app.route('/job-offers/<job_id>', methods=['DELETE'])
def delete_job_offer(job_id):
    return delete_job_offer_by_id(job_id)

@app.route('/job-offers', methods=['GET'])
def list_job_offers():
    return list_all_job_offers()

@app.route('/job-offers/by-user/<user_id>', methods=['GET'])
def list_jobs_by_user(user_id):
    return get_jobs_by_user(user_id)

@app.route('/job-offers/<job_id>', methods=['GET'])
def get_job_offer(job_id):
    return get_job_offer_by_id(job_id)

@app.route('/job-offers/<job_id>', methods=['PUT'])
def update_job_offer(job_id):
    update_data = request.json
    return update_job_offer_by_id(job_id, update_data)

@app.route('/search-job-offers', methods=['GET'])
def search_jobs():
    return search_job_offers()


@app.route('/users/<user_id>/cvs', methods=['POST'])
def add_cv_for_user(user_id):
    if 'file' not in request.files:
        return jsonify({'error': 'CV PDF file is required'}), 400

    file = request.files['file']
    title = request.form.get('title')
    visibility = request.form.get('visibility', 'private')
    
    cv_txt = request.form.get('cv_txt')
    expertise_raw = request.form.get('expertise')
    try:
        expertise = json.loads(expertise_raw) if expertise_raw else {}
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in expertise field'}), 400

    response, status_code = add_cv(user_id, file, title,expertise, cv_txt, visibility)
    return jsonify(response), status_code


@app.route("/users/<user_id>/cvs", methods=["GET"])
def get_user_cvs(user_id):
    return get_all_user_cvs(user_id)



@app.route("/users/<user_id>/cvs/<cv_id>", methods=["PUT"])
def update_cv(user_id, cv_id):
    data = request.json
    return update_user_cv(user_id, cv_id, data)





@app.route("/users/<user_id>/cvs/<cv_id>", methods=["DELETE"])
def delete_cv(user_id, cv_id):
    return delete_user_cv(user_id, cv_id)


@app.route("/cvs/public", methods=["GET"])
def get_public_cvs():
    return get_all_public_cvs()




@app.route('/cvs/search', methods=['GET'])
def search_public_cvs():
    query = request.args.get('q', '')
    response, status_code = search_public_cvs_logic(query)
    return jsonify(response), status_code



@app.route('/cvs/download/<cv_id>', methods=['GET'])
def download_cv(cv_id):
    response, status_code = download_cv_logic(cv_id)
    if isinstance(response, dict):
        return jsonify(response), status_code
    return response


@app.route("/cv-chat/<cv_id>", methods=["POST"])
def cv_chat(cv_id):
    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Missing 'question'"}), 400


    cv = mongo.db.cvs.find_one({"_id": ObjectId(cv_id)})
    cv_txt = cv.get("cv_txt")

    # Call your chat function
    answer ,history= get_cv_chat_response(cv_id,cv_txt, question)
        # Optionally return full history for UI

    return jsonify({"answer": answer, "history": history}), 200

@app.route("/cv-analysis/<cv_id>", methods=["POST"])
def cv_analysis(cv_id):
    if not cv_id:
        return jsonify({"error": "Missing 'cv_id'"}), 400

    response, status = get_cv_file_path(cv_id)
    if status != 200:
        return response, status

    pdf_path = r"{}".format(response.get_json()["file_path"])
    cv_text = extract_text_from_pdf(pdf_path)

    if not cv_text:
        return jsonify({"error": "Failed to extract text from PDF"}), 500

    try:
        analysis_result = analyze_cv_text(cv_text)
    except ValueError as e:
        return jsonify({
            "error": str(e),
        }), 500

    return jsonify({
        "cv_analysis": analysis_result
    }), 200

@app.route('/cv-path/<cv_id>')
def get_cv_path_url(cv_id):
    return get_cv_path(cv_id)

@app.route('/cv/<cv_id>')
def get_cv(cv_id):
    return get_cv_by_id(cv_id)

@app.route('/static/uploads/cvs/<filename>')
def download_cv_file(filename):
    return send_from_directory('uploads/cvs', filename)
    
@app.route("/cv-analysis-text", methods=["POST"])
def cv_analysis_text():
    data = request.get_json()

    if not data or "cv_txt" not in data:
        return jsonify({"error": "Missing 'cv_txt'"}), 400

    cv_text = data["cv_txt"]

    if not cv_text.strip():
        return jsonify({"error": "CV text is empty"}), 400

    try:
        analysis_result = analyze_cv_text_skills(cv_text)
    except ValueError as e:
        return jsonify({
            "error": str(e),
        }), 500

    return jsonify({
        "owner": analysis_result.get("owner", ""),
        "contact": analysis_result.get("contact", {}),
        "technologies": analysis_result.get("technologies", []),
        "skills": analysis_result.get("skills", []),
        "experience": analysis_result.get("experience", []),
        "levels": analysis_result.get("levels", {}),
        "education": analysis_result.get("education", []),
        "languages": analysis_result.get("languages", []),
        "snapshot": analysis_result.get("snapshot", ""),
        "hashtags": analysis_result.get("hashtags", []),
        "certifications": analysis_result.get("certifications", []),
        "atouts": analysis_result.get("atouts", []),
    }), 200

@app.route('/create-job-offer-from-url/<user_id>', methods=['POST'])
def create_job_offer_from_url_route(user_id):
    data = request.json
    job_url = data.get("job_url")
    visibility = data.get("visibility")

    if not job_url:
        return jsonify({"error": "Missing job_url"}), 400

    response, status = create_job_offer_from_linkedin_url(user_id, job_url, visibility)
    return jsonify(response), status
    
@app.route('/applications/<candidate_id>', methods=['GET'])
def get_applications_by_candidate(candidate_id):
    return list_applications_by_candidate(candidate_id)

@app.route('/applications/job/<job_id>', methods=['GET'])
def get_applications_by_job(job_id):
    return list_applications_by_job(job_id)

@app.route('/applications', methods=['GET'])
def get_all_applications():
    return list_all_applications()

@app.route("/apply", methods=["POST"])
def apply():
    data = request.json
    candidate_id = data.get("candidate_id")
    job_id = data.get("job_id")
    cv_id = data.get("cv_id")

    if not candidate_id or not job_id or not cv_id:
        return jsonify({"error": "Missing 'candidate_id', 'job_id' or 'cv_id'"}), 400

    return apply_to_job(candidate_id, job_id, cv_id)


@app.route('/start', methods=['POST'])
def start_interview():
    data = request.json
    application_id = data.get("application_id")

    if not application_id:
        return jsonify({"error": "Missing application_id"}), 400

    response, status_code = start_interview_process(application_id)
    return jsonify(response), status_code

@app.route('/answer', methods=['POST'])
def handle_answer():
    data = request.json
    application_id = data.get("application_id")
    user_answer = data.get("answer")

    response, status_code = handle_answer_process(application_id, user_answer)
    return jsonify(response), status_code

@app.route('/conversation/<application_id>', methods=['GET'])
def get_conversation(application_id):
    response, status_code = get_conversation_data(application_id)
    return jsonify(response), status_code

@app.route('/generate-report', methods=['POST'])
def generate_report_endpoint():
    data = request.json
    application_id = data.get('application_id')

    if not application_id:
        return jsonify({"error": "application_id is required"}), 400

    try:
        pdf_path = generate_candidate_report(application_id)
        return jsonify({"message": f"✅ Report successfully generated: {pdf_path}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/report-path/<application_id>', methods=['GET'])
def get_report_path(application_id):
    try:
        application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})
        if not application:
            return jsonify({"error": "Application not found"}), 404
        
        report_path = application.get("report_path")
        if not report_path:
            return jsonify({"error": "Report not found for this application"}), 404
        
        return jsonify({
            "source": "http://127.0.0.1:5000/static/"+report_path ,  # convert to full URL
            "name": os.path.basename(report_path)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/static/uploads/report/<filename>')
def download_report_file(filename):
    return send_from_directory('uploads/report', filename)
# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)