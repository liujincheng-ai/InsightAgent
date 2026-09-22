import os

import pandas as pd
from flask import Flask, jsonify, request

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    # Optional: Parse Excel to validate it works
    try:
        df = pd.read_excel(file_path)
        columns = df.columns.tolist()
        return jsonify({"message": "File uploaded successfully", "columns": columns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/query_excel", methods=["POST"])
def query_excel():
    data = request.json
    file_name = data.get("file_name")
    query = data.get("query")

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    try:
        df = pd.read_excel(file_path)
        # Placeholder logic for querying the Excel file:
        # This should be replaced with InsightAgent integration for natural language queries.
        response = f"Query on {len(df)} rows completed."
        return jsonify({"query_result": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
