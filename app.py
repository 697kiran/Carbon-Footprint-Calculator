from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def health_check():
    return jsonify({"status": "ready", "version": "1.0.0"})

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        activities = data.get('activities', [])

        for idx, activity in enumerate(activities):
            if 'name' not in activity:
                activity['name'] = f"Activity {idx + 1}"

        input_data = {
            "activities": activities,
            "api_key": os.getenv("CLIMATIQ_API_KEY")
        }

        result = subprocess.run(
            ['python', 'check_api.py'],
            input=json.dumps(input_data),
            text=True,
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500

        return jsonify(json.loads(result.stdout))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.getenv("CLIMATIQ_API_KEY"):
        print("Warning: CLIMATIQ_API_KEY not set in environment variables")

    app.run(host='0.0.0.0', port=5000, debug=True)