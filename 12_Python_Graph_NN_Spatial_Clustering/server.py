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
import traceback
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import gnn_geodemographic

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
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    ok = True

    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        try:
            gnn_geodemographic.run_pipeline(k=k, layers=layers, verbose=True)
        except Exception:
            ok = False
            traceback.print_exc()

    return jsonify({
        'ok': ok,
        'stdout': out_buf.getvalue(),
        'stderr': err_buf.getvalue(),
    })


if __name__ == '__main__':
    print('Geodemographic Lab  ->  http://localhost:8000')
    app.run(port=8000, debug=False)
