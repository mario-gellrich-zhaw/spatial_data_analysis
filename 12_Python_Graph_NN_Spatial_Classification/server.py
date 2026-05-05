"""
Flask dev server for the geodemographic lab.

Replaces `python -m http.server 8000`.  Adds a /run-gnn endpoint so the
browser can trigger gnn_geodemographic.py without leaving the page.

Usage:
    conda activate gisenv
    python server.py
    # open http://localhost:8000
"""

from flask import Flask, jsonify, request, send_from_directory
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
app  = Flask(__name__)


@app.route('/')
def index():
    return send_from_directory(BASE, 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE, filename)


@app.route('/health')
def health():
    return jsonify({'ok': True})


@app.route('/run-gnn', methods=['POST'])
def run_gnn():
    body   = request.get_json(silent=True) or {}
    k      = int(body.get('k', 5))
    layers = int(body.get('layers', 2))
    result = subprocess.run(
        [sys.executable, str(BASE / 'gnn_geodemographic.py'), '--k', str(k), '--layers', str(layers)],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )
    return jsonify({
        'ok':     result.returncode == 0,
        'stdout': result.stdout,
        'stderr': result.stderr,
    })


if __name__ == '__main__':
    print('Geodemographic Lab  →  http://localhost:8000')
    app.run(port=8000, debug=False)
