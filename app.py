import os
import tempfile
import json
from flask import Flask, render_template, request, send_file, jsonify, Response
import scraper

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_scraper():
    try:
        search_query = request.form.get("search_query", "").strip()
        max_results = request.form.get("max_results", "").strip()
        output_file = request.form.get("output_file", "").strip()

        if not search_query:
            return jsonify({"error": "Search query is required"}), 400

        if not max_results.isdigit():
            return jsonify({"error": "Max results must be a number"}), 400

        if not output_file.endswith(".xlsx"):
            return jsonify({"error": "Output file must end with .xlsx"}), 400

        # Use a cross-platform temporary directory
        file_path = os.path.join(tempfile.gettempdir(), output_file)

        # Inject values BEFORE running scraper
        scraper.SEARCH_QUERY = search_query
        scraper.MAX_RESULTS = int(max_results)
        scraper.OUTPUT_FILE = file_path

        def generate():
            try:
                for msg in scraper.run_scraper():
                    # If it's the final message, add the download filename
                    if msg["type"] == "done":
                        msg["filename"] = os.path.basename(msg["file"])
                        msg["download_url"] = f"/download/{msg['filename']}"
                    
                    yield f"data: {json.dumps(msg)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return Response(generate(), mimetype="text/event-stream")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(file_path):
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    return "File not found", 404


if __name__ == "__main__":
    app.run(debug=True)
