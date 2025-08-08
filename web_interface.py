import os, json, time, logging
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from app.realtime import get_or_create_session, push_caption, pop_event_generator, get_session_manager
from app.ide_workflow import (
    generate_code_for_jira_task,
    run_tests,
    commit_changes,
    open_pull_request,
)

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


# --- IDE Bridge Actions ---
@app.route('/api/ide/generate-code', methods=['POST'])
def ide_generate_code():
    """Generate code for a Jira task with confirmation."""
    data = request.get_json(force=True) or {}
    if not data.get('confirm'):
        return jsonify({'requires_confirmation': True, 'action': 'generate_code'}), 400
    task_key = data.get('task_key', '')
    code = generate_code_for_jira_task(task_key)
    return jsonify({'code': code})


@app.route('/api/ide/run-tests', methods=['POST'])
def ide_run_tests():
    """Run project tests with confirmation."""
    data = request.get_json(force=True) or {}
    if not data.get('confirm'):
        return jsonify({'requires_confirmation': True, 'action': 'run_tests'}), 400
    output = run_tests()
    return jsonify({'output': output})


@app.route('/api/ide/commit', methods=['POST'])
def ide_commit():
    """Commit changes with confirmation."""
    data = request.get_json(force=True) or {}
    if not data.get('confirm'):
        return jsonify({'requires_confirmation': True, 'action': 'commit'}), 400
    message = data.get('message', 'AI commit')
    commit_hash = commit_changes(message)
    return jsonify({'commit': commit_hash})


@app.route('/api/ide/open-pr', methods=['POST'])
def ide_open_pr():
    """Open a pull request with confirmation."""
    data = request.get_json(force=True) or {}
    if not data.get('confirm'):
        return jsonify({'requires_confirmation': True, 'action': 'open_pr'}), 400
    owner = data.get('owner')
    repo = data.get('repo')
    head = data.get('head')
    base = data.get('base', 'main')
    title = data.get('title')
    body = data.get('body', '')
    pr = open_pull_request(owner, repo, head, base, title, body)
    return jsonify({'pr': pr})

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
