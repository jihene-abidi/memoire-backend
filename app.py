from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from db import mongo,mail
from job import create_job_offers,delete_job_offer_by_id,list_all_job_offers,update_job_offer_by_id,get_job_offer_by_id,search_job_offers
from users import signup,verify_email_token,update_user_profile,sign_in_user,update_profile_image,request_reset_password_logic,reset_password_logic,get_all_users,get_user_by_id,get_role_by_id
from flask_cors import CORS


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
# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)

