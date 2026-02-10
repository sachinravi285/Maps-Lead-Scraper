import os
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/render/.cache/ms-playwright"

from flask import Flask, render_template, request, send_file
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
            return "Search query is required"

        if not max_results.isdigit():
            return "Max results must be a number"

        if not output_file.endswith(".xlsx"):
            return "Output file must end with .xlsx"

        # Always save in /tmp (Render writable directory)
        file_path = os.path.join("/tmp", output_file)

        # Inject values BEFORE running scraper
        scraper.SEARCH_QUERY = search_query
        scraper.MAX_RESULTS = int(max_results)
        scraper.OUTPUT_FILE = file_path

        # Run scraper
        scraper.run_scraper()

        if not os.path.exists(file_path):
            return "File not generated"

        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    app.run()
