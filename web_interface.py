import os, json, time, logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
LOG_PATH = os.getenv('MENTOR_EVENTS_LOG', 'data/meeting_events.log')
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'ts': time.time()})

@app.route('/api/meeting-events', methods=['POST'])
def meeting_events():
    try:
        payload = request.get_json(force=True) or {}
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload) + '\n')
        # TODO: route to realtime pipeline (ASR/diarization/question detection)
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.exception('meeting-events failed')
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port)