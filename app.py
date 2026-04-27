from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import mysql.connector
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import requests
import whisper
import os
from zoneinfo import ZoneInfo
import pytz
from datetime import datetime

app = Flask(__name__)
CORS(app)

# -------------------------
# MySQL Connection
# -------------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Priya@123",
    database="school"
)

cursor = db.cursor(dictionary=True)

# -------------------------
# Whisper Model
# -------------------------
model = whisper.load_model("base")

# -------------------------
# Twilio Config
# -------------------------
account_sid = "##########"
auth_token = "###########"
twilio_number = "##########"

client = Client(account_sid, auth_token)

# ⚠️ IMPORTANT (NO SPACE)
BASE_URL = "#########"

# -------------------------
# Home
# -------------------------
@app.route("/")
def home():
    return "Backend Running Successfully 🚀"

# -------------------------
# Make Call
# -------------------------
def make_call(phone):

    call = client.calls.create(
        to=phone,
        from_=twilio_number,
        url=f"{BASE_URL}/voice",
        status_callback=f"{BASE_URL}/call-status",
        status_callback_event=["completed"],
        status_callback_method="POST"
    )

    return call.sid

# -------------------------
# Voice Message
# -------------------------
@app.route("/voice", methods=["GET","POST"])
def voice():

    response = VoiceResponse()

    response.say(
        "Why is your child absent today. Please say the reason after the beep.",
        voice="alice"
    )

    response.record(
        max_length=10,
        play_beep=True,
        action=f"{BASE_URL}/recording"
    )

    response.say("Thank you")

    return str(response)

# -------------------------
# Recording Route
# -------------------------
@app.route("/recording", methods=["POST"])
def recording():

    try:

        recording_url = request.form.get("RecordingUrl")
        call_sid = request.form.get("CallSid")

        audio = requests.get(
            recording_url + ".wav",
            auth=(account_sid, auth_token)
        )

        os.makedirs("recordings", exist_ok=True)

        file_path = f"recordings/{call_sid}.wav"

        with open(file_path, "wb") as f:
            f.write(audio.content)

        result = model.transcribe(file_path)
        reason = result["text"]

        cursor.execute(
            "UPDATE responses SET reason=%s WHERE call_sid=%s",
            (reason, call_sid)
        )

        db.commit()

        return "OK"

    except Exception as e:

        print("Recording Error:", e)
        return "Error"

# -------------------------
# Download Attendance Report
# -------------------------
@app.route("/download-report")
def download_report():

    cursor.execute("""
        SELECT roll_no, name, phone, status, reason, date_time
        FROM responses
        ORDER BY date_time DESC
    """)

    data = cursor.fetchall()

    df = pd.DataFrame(data)

    file_name = "attendance_report.csv"
    df.to_csv(file_name, index=False)

    return send_file(file_name, as_attachment=True)

# -------------------------
# Missed Call → SMS
# -------------------------
@app.route("/call-status", methods=["POST"])
def call_status():

    call_status = request.form.get("CallStatus")
    call_sid = request.form.get("CallSid")

    if call_status in ["busy","no-answer","failed"]:

        cursor.execute(
            "SELECT phone FROM responses WHERE call_sid=%s",
            (call_sid,)
        )

        data = cursor.fetchone()

        if data:

            client.messages.create(
                body="Your child is absent today. Please inform the reason.",
                from_=twilio_number,
                to=data["phone"]
            )

    return "OK"

# -------------------------
# Upload CSV
# -------------------------
@app.route("/upload", methods=["POST"])
def upload():

    file = request.files["file"]
    df = pd.read_csv(file, header=None)

    for roll in df[0]:

        cursor.execute(
            "SELECT * FROM students WHERE roll_no=%s",
            (roll,)
        )

        student = cursor.fetchone()

        if student:

            phone = "+91" + str(student["phone"])

            call_sid = make_call(phone)

            from datetime import datetime, timedelta

            ist = pytz.timezone("Asia/Kolkata")
            current_time = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """
                INSERT INTO responses
                (roll_no, name, phone, status, call_sid, date_time)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    student["roll_no"],
                    student["name"],
                    phone,
                    "Call Sent",
                    call_sid,
                    current_time
                )
            )

    db.commit()

    return jsonify({"message":"Calls started"})

# -------------------------
# Dashboard API
# -------------------------
@app.route("/responses")
def responses():

    cursor.execute("SELECT * FROM responses ORDER BY date_time DESC")

    data = cursor.fetchall()

    return jsonify(data)

# -------------------------
# Run Server
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)