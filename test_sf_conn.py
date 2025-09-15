# Final_Code/integration/flask_app.py
from flask import Flask, request, jsonify
import os
import requests # Ensure this import is present
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv() 
# from upload_audio import save_and_upload_audio_bytes
# from transcription.transcribe_audio import transcribe_audio
# from summarization.summarize_conversation import process_conversation

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SF_CLIENT_ID = os.getenv("SF_CLIENT_ID")
SF_CLIENT_SECRET = os.getenv("SF_CLIENT_SECRET")
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_TOKEN = os.getenv("SF_TOKEN")
SF_DOMAIN = "https://360one--wealthuat.sandbox.my.salesforce.com"
SF_AUTH_URL = os.getenv("SF_AUTH_URL", "https://test.salesforce.com/services/oauth2/token")

SF_API_VERSION = "v63.0"
def get_salesforce_token():
# 1) Load required env vars
    SF_CLIENT_ID = os.getenv("SF_CLIENT_ID")
    SF_CLIENT_SECRET = os.getenv("SF_CLIENT_SECRET")
    SF_USERNAME = os.getenv("SF_USERNAME")
    SF_PASSWORD = os.getenv("SF_PASSWORD")
    SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "") # token may be empty if IP is whitelisted

    # 2) Validate: fail early with a clear message
    missing = [k for k, v in {
    "SF_CLIENT_ID": SF_CLIENT_ID,
    "SF_CLIENT_SECRET": SF_CLIENT_SECRET,
    "SF_USERNAME": SF_USERNAME,
    "SF_PASSWORD": SF_PASSWORD,
    # security token intentionally not required
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Salesforce env vars: {', '.join(missing)}")

    # 3) Safe concat (treat None as empty)
    password_with_token = (SF_PASSWORD or "") + (SF_SECURITY_TOKEN or "")

    data = {
    "grant_type": "password",
    "client_id": SF_CLIENT_ID,
    "client_secret": SF_CLIENT_SECRET,
    "username": SF_USERNAME,
    "password": password_with_token
    }

    # 4) Request token
    resp = requests.post(SF_AUTH_URL, data=data, timeout=30)
    if resp.status_code != 200:
    # Surface exact Salesforce error (but don’t log secrets)
        raise RuntimeError(f"Salesforce login failed: {resp.text}")

    j = resp.json()
    print(j)
    access_token = j.get("access_token")
    instance_url = j.get("instance_url")
    if not access_token or not instance_url:
        raise RuntimeError(f"Salesforce login missing fields: {j}")

    return access_token, instance_url
# --- Flask app ---
app = Flask(__name__)
@app.route("/save_to_salesforce", methods=["POST"])
def save_to_salesforce():
    try:
        data = request.json
        account_id = data.get("AccountID")
        cr_rm_name = data.get("CR_RM_Name__c")
        amc_rm_name = data.get("AMC_RM_Name__c")
        summary = data.get("summary")
        print(account_id, cr_rm_name, amc_rm_name, summary)

        if not all([account_id, cr_rm_name, amc_rm_name, summary]):
            print("@@@@@@@@@@@@@")
            return jsonify({"error": "Missing required fields"}), 400

        # Get Salesforce token and instance URL
        access_token, instance_url = get_salesforce_token()

        # Prepare Task payload
        task_data = {
        "Subject": "AI Generated Call Summary",
        "Description": summary,
        "WhatId": account_id,# Link Task to Account
        "OwnerId": amc_rm_name, # Assign to AMC RM (User/Queue ID)
        "WhoId": cr_rm_name # Link to CR RM (Contact/Lead ID)
        }

        headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
        }

        # Use instance_url returned from Salesforce login
        task_url = f"{instance_url}/services/data/v63.0/sobjects/Task"
        resp = requests.post(task_url, headers=headers, json=task_data)
        if resp.status_code == 201:
            return jsonify({"success": True, "data": resp.json(), "message": "Task created successfully"}), 201
        else:
            return jsonify({"error": f"Failed to create task: {resp.text}", "status": resp.status_code}), resp.status_code

        # return jsonify(resp.json()), resp.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Optional: base folder for conversations
# BASE_CONVERSATION_FOLDER = "/home/ubuntu/Summary/final_code/conversations"
# Path(BASE_CONVERSATION_FOLDER).mkdir(parents=True, exist_ok=True)

# @app.route("/upload", methods=["POST"])
# def upload_audio():
#     if "file" not in request.files:
#         return jsonify({"error": "No file part in request"}), 400
#     file = request.files["file"]
#     if file.filename == "":
#         return jsonify({"error": "No selected file"}), 400

#     try:
#         audio_bytes = file.read()
#         upload_result = save_and_upload_audio_bytes(audio_bytes, original_filename=file.filename)
#         return jsonify(upload_result), 200
#     except Exception as e:
#         logger.exception("Upload failed")
#         return jsonify({"error": str(e)}), 500

# @app.route("/transcribe", methods=["POST"])
# def run_transcription():
#     conversation_folder = request.json.get("conversation_folder") if request.is_json else None
#     if not conversation_folder or not os.path.exists(conversation_folder):
#         return jsonify({"error": "Valid conversation folder required"}), 400

#     try:
#         # Path to the audio.wav inside this conversation folder
#         audio_path = os.path.join(conversation_folder, "audio.wav")
#         if not os.path.exists(audio_path):
#             return jsonify({"error": f"No audio.wav found in {conversation_folder}"}), 400

#         # Pass both audio_path and conversation_folder
#         transcription_file = transcribe_audio(audio_path, conversation_folder)
#         return jsonify({"transcription_file": transcription_file}), 200
#     except Exception as e:
#         logger.exception("Transcription failed")
#         return jsonify({"error": str(e)}), 500

# @app.route("/summarize", methods=["POST"])
# def run_summary():
#     conversation_folder = request.json.get("conversation_folder") if request.is_json else None
#     if not conversation_folder or not os.path.exists(conversation_folder):
#         return jsonify({"error": "Valid conversation folder required"}), 400
#     try:
#         summary_file = process_conversation(conversation_folder)
#         with open(summary_file, "r") as f:
#             summary_text = f.read()
#         return jsonify({"summary": summary_text}), 200
#     except Exception as e:
#         logger.exception("Summarization failed")
#         return jsonify({"error": str(e)}), 500

# if __name__ == "__main__":
#     # HTTPS
#     context = ("/home/ubuntu/Summary/server/cert.pem", "/home/ubuntu/Summary/server/key.pem")
#     app.run(host="0.0.0.0", port=8003, ssl_context=context)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

