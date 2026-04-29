# mock_server.py
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/ai/input", methods=["POST"])
def ai_input():
    data = request.json
    print(f"\n📥 Gelen istek:")
    print(f"   cameraId: {data.get('cameraId')}")
    print(f"   moduleId: {data.get('moduleId')}")
    print(f"   triggeredAt: {data.get('triggeredAt')}")
    print(f"   data: {data.get('data')}")
    print(f"   message: {data.get('message')}")

    # API key kontrolü
    api_key = request.headers.get("X-API-KEY")
    if api_key != "test-key-123":
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({"status": "ok", "received": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085, debug=True)