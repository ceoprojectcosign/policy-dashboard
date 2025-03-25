from flask import Flask, render_template, render_template_string, url_for, request
import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import fitz  # PyMuPDF
import re

app = Flask(__name__)

@app.route("/")
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Policy Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 text-gray-900 font-sans">
        <div class="max-w-3xl mx-auto py-10 px-6">
            <h1 class="text-4xl font-bold mb-6">District Policy Dashboard</h1>
            <form action="/search" method="get" class="mb-6">
                <input name="q" placeholder="Search policies..." class="w-full p-3 border rounded-lg" />
            </form>
            <h2 class="text-2xl font-semibold mb-4">Browse by Series</h2>
            <ul class="grid grid-cols-2 gap-4">
                {% for series in ['0000', '1000', '2000', '3000', '4000', '5000', '6000'] %}
                    <li>
                        <a href="/series/{{ series }}" class="block bg-white p-4 rounded-lg shadow hover:bg-gray-50">
                            Series {{ series }}
                        </a>
                    </li>
                {% endfor %}
            </ul>
        </div>
    </body>
    </html>
    """)

@app.route("/policy/<series_id>/<policy_id>")
def view_policy(series_id, policy_id):
    cache_file = f"cache/{series_id}_{policy_id}.txt"

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            text = f.read()
        from_cache = True
        pdf_url = "#"  # still safe to show "Download" button but non-functional
    else:
        series_url_part = {
            "0000": "464-Series-0000---District-Wide",
            "1000": "465-Series-1000---The-Board-of-Directors",
            "2000": "466-Series-2000---Instruction",
            "3000": "467-Series-3000---Students",
            "4000": "468-Series-4000---Community-Relations",
            "5000": "469-Series-5000---Personnel",
            "6000": "470-Series-6000---Management-Support",
        }.get(series_id)

        if not series_url_part:
            return f"<h1>Error:</h1><p>Series {series_id} not found.</p>"

        base_url = f"https://www.asd103.org/District/{series_url_part}.html"
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find matching PDF link
        pdf_url = ""
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            if href.endswith(".pdf") and policy_id in text.replace("-", "").replace(",", ""):
                pdf_url = urllib.parse.urljoin(base_url, href)
                break

        if not pdf_url:
            pdf_url = "#"
            text = "⚠️ The original PDF could not be found for this policy."
            from_cache = False
        else:
            try:
                pdf_response = requests.get(pdf_url)
                doc = fitz.open(stream=pdf_response.content, filetype="pdf")
                text = "\n".join([page.get_text() for page in doc])
                doc.close()
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(text)
                from_cache = False
            except Exception as e:
                return f"<h1>PDF Parsing Error:</h1><p>{str(e)}</p>"

    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Policy {policy_id}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 text-gray-900 font-sans">
        <div class="max-w-5xl mx-auto py-10 px-6">
            <a href="/series/{series_id}" class="text-blue-600 underline hover:text-blue-800">&larr; Back to Series {series_id}</a>
            <h1 class="text-3xl font-bold mt-4 mb-2">Policy {policy_id} - Series {series_id}</h1>
            <p class="text-sm text-gray-500 mb-4">Source: {"Cached" if from_cache else "Live parsed"}</p>
            {'<a href="' + pdf_url + '" target="_blank" class="inline-block mb-6 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition">Download Original PDF</a>' if pdf_url != "#" else '<p class="text-sm text-red-500 mb-6">Original PDF not available for this policy.</p>'}
            <div class="bg-white p-6 rounded-xl shadow overflow-x-auto whitespace-pre-wrap text-sm leading-relaxed">
                {text}
            </div>
        </div>
    </body>
    </html>
    """)

@app.route("/series/<series_id>")
def series(series_id):
    series_url_part = {
        "0000": "464-Series-0000---District-Wide",
        "1000": "465-Series-1000---The-Board-of-Directors",
        "2000": "466-Series-2000---Instruction",
        "3000": "467-Series-3000---Students",
        "4000": "468-Series-4000---Community-Relations",
        "5000": "469-Series-5000---Personnel",
        "6000": "470-Series-6000---Management-Support",
    }.get(series_id)

    if not series_url_part:
        return f"<h1>Error:</h1><p>Series {series_id} not found.</p>"

    url = f"https://www.asd103.org/District/{series_url_part}.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    policies = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text(strip=True)
        if href.endswith(".pdf") and text:
            policy_id = text.split()[0].replace("-", "").replace(",", "")
            full_url = urllib.parse.urljoin(url, href)
            policies.append({
                "title": text,
                "url": full_url,
                "id": policy_id,
            })

    return render_template("series.html", series_id=series_id, policies=policies)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return "<h1>Please enter a search term.</h1>"

    results = []

    for filename in os.listdir("cache"):
        if filename.endswith(".txt"):
            filepath = os.path.join("cache", filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if query in content.lower():
                base = filename.replace(".txt", "")
                series_id, policy_id = base.split("_")
                preview_start = content.lower().find(query)
                snippet = content[preview_start:preview_start + 200].replace("\n", " ") + "..."

                results.append({
                    "series_id": series_id,
                    "policy_id": policy_id,
                    "snippet": snippet
                })

# Highlight query in results (case-insensitive)
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for result in results:
        result["highlighted_snippet"] = pattern.sub(
            lambda m: f"<mark>{m.group(0)}</mark>", result["snippet"]
        )
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Search Results</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 text-gray-900 font-sans">
        <div class="max-w-4xl mx-auto py-10 px-6">
            <form action="/search" method="get">
                <input type="text" name="q" placeholder="Search policies..." value="{{ query }}" class="w-full p-3 border rounded-lg mb-6" />
            </form>
            <h1 class="text-2xl font-bold mb-4">Search Results for "{{ query }}"</h1>
            {% if results %}
                <ul class="space-y-4">
                {% for r in results %}
                    <li class="bg-white p-4 rounded-lg shadow">
                        <a class="text-blue-600 font-semibold text-lg" href="/policy/{{ r.series_id }}/{{ r.policy_id }}">
                            Series {{ r.series_id }} – Policy {{ r.policy_id }}
                        </a>
                        <p class="text-sm text-gray-600 mt-1">{{ r.highlighted_snippet | safe }}</p>
                    </li>
                {% endfor %}
                </ul>
            {% else %}
                <p>No results found.</p>
            {% endif %}
            <p class="mt-6"><a href="/" class="text-blue-600 underline">&larr; Back to Home</a></p>
        </div>
    </body>
    </html>
    """, query=query, results=results)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
