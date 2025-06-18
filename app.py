from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from db import mongo,mail
from job import create_job_offers,delete_job_offer_by_id,list_all_job_offers,update_job_offer_by_id,get_job_offer_by_id,search_job_offers
from users import signup,verify_email_token,update_user_profile,sign_in_user,update_profile_image,request_reset_password_logic,reset_password_logic,get_all_users,get_user_by_id,get_role_by_id
from flask_cors import CORS
from flask import send_from_directory
from cv import get_all_user_cvs, add_cv, update_user_cv, delete_user_cv, get_all_public_cvs, search_public_cvs_logic, download_cv_logic, get_cv_file_path, get_cv_path,get_cv_by_id
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

    response, status_code = add_cv(user_id, file, title, visibility)
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

    # Get the file path response
    response, status = get_cv_file_path(cv_id)

    # If the CV isn’t found
    if status != 200:
        return response, status


    # Extract the actual path from the JSON response
    pdf_path = response.get_json()["file_path"]


    pdf_path = r"{}".format(pdf_path)

    # Extract text from PDF
    cv_text = extract_text_from_pdf(pdf_path)
    if not cv_text:
        return jsonify({"error": "Failed to extract text from PDF"}), 500

    # Call your chat function
    answer ,history= get_cv_chat_response(cv_id,cv_text, question)
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
    
# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)
