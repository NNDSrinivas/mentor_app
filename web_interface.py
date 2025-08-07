import os, json, time, logging
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from app.realtime import get_or_create_session, push_caption, pop_event_generator

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'ts': time.time()})

@app.route('/api/meeting-events', methods=['POST'])
def meeting_events():
    payload = request.get_json(force=True) or {}
    action = payload.get('action')
    data = payload.get('data', {})
    mid = (data.get('meetingId') or data.get('id') or 'default_meeting')
    ic = data.get('icLevel', 'IC6')
    sess = get_or_create_session(mid, ic_level=ic)

    if action == 'caption_chunk':
        text = data.get('text') or data.get('caption') or ''
        speaker = data.get('speaker')
        push_caption(mid, text=text, speaker=speaker)
        return jsonify({'ok': True, 'queued': len(text)})
    elif action in ('meeting_detected','start_recording','stop_recording','speaker_change','screen_shared'):
        return jsonify({'ok': True})
    else:
        return jsonify({'ok': False, 'error': 'unknown action'}), 400

@app.route('/api/answer-stream/<meeting_id>')
def answer_stream(meeting_id: str):
    def gen():
        for chunk in pop_event_generator(meeting_id):
            yield chunk
    return Response(gen(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port, threaded=True)