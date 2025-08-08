import os, json, time, logging
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from app.realtime import get_or_create_session, push_caption, pop_event_generator, get_session_manager

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'ts': time.time()})

# New session-based API endpoints for Wave 3
@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new interview session"""
    try:
        data = request.get_json() or {}
        session_manager = get_session_manager()
        session_id = session_manager.create_session(data)
        return jsonify({'session_id': session_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>/stream')
def session_stream(session_id: str):
    """SSE stream for session events"""
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    def event_stream():
        client_id = f"sse_{session_id}_{time.time()}"
        client_queue = session.add_client_queue(client_id)
        
        try:
            # Send recent answers to new client
            for answer in session.get_recent_answers():
                event_data = {
                    'type': 'historical_answer',
                    'data': answer
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            # Stream new events
            while True:
                try:
                    data = client_queue.get(timeout=30)
                    yield f"data: {data}\n\n"
                except:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        except GeneratorExit:
            pass
        finally:
            session.remove_client_queue(client_id)
    
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/sessions/<session_id>/captions', methods=['POST'])
def add_caption(session_id: str):
    """Add a caption to a session"""
    try:
        data = request.get_json() or {}
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        session.add_caption(data)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>/answers')
def get_session_answers(session_id: str):
    """Get all answers for a session"""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        answers = session.get_recent_answers(limit=50)
        return jsonify({'answers': answers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def end_session(session_id: str):
    """End a session"""
    try:
        session_manager = get_session_manager()
        session_manager.end_session(session_id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Legacy API endpoints for backward compatibility
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