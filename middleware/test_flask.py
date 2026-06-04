#!/usr/bin/env python3
"""Minimal Flask test"""
from flask import Flask, request, Response
import json

app = Flask(__name__)

@app.route('/test', methods=['POST'])
def test():
    data = request.get_json()
    return Response(json.dumps({'status': 'success', 'data': data}), mimetype='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
