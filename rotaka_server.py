"""
Rotaka Multiplayer Relay Server
Flask-SocketIO WebSocket relay — no game logic, just routes events between two players.

Run locally:
    pip install -r requirements.txt
    python rotaka_server.py

Deploy to Render.com:
    See render.yaml
"""

import random
import string
import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rotaka-dev-secret')

socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading',
    logger=False,
    engineio_logger=False,
)

# rooms: { room_id: { 'players': [sid, ...], 'colors': {sid: 'Beyaz'|'Siyah'} } }
rooms: dict = {}


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def gen_room_id(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        rid = ''.join(random.choices(chars, k=length))
        if rid not in rooms:
            return rid


def other_player(room: dict, sid: str):
    """Return the SID of the other player in the room, or None."""
    for s in room['players']:
        if s != sid:
            return s
    return None


# ─── STATIC FILE ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'rotaka.html')


# ─── SOCKET EVENTS ────────────────────────────────────────────────────────────

@socketio.on('create_room')
def handle_create_room():
    """Player A creates a new room and becomes Beyaz."""
    rid = gen_room_id()
    rooms[rid] = {
        'players': [request.sid],
        'colors':  {request.sid: 'Beyaz'},
    }
    join_room(rid)
    emit('room_created', {'room_id': rid, 'your_color': 'Beyaz'})
    print(f'[Room {rid}] created by {request.sid[:8]}')


@socketio.on('join_room_req')
def handle_join_room(data: dict):
    """Player B joins an existing room and becomes Siyah."""
    rid = data.get('room_id', '').strip().upper()

    if rid not in rooms:
        emit('join_error', {'msg': 'Oda bulunamadı. Kodu kontrol et.'})
        return

    room = rooms[rid]

    if len(room['players']) >= 2:
        emit('join_error', {'msg': 'Bu oda zaten dolu.'})
        return

    if request.sid in room['players']:
        emit('join_error', {'msg': 'Zaten bu odadasın.'})
        return

    room['players'].append(request.sid)
    room['colors'][request.sid] = 'Siyah'
    join_room(rid)

    # Notify Player B
    emit('game_start', {'your_color': 'Siyah', 'room_id': rid})
    # Notify Player A
    opp = other_player(room, request.sid)
    if opp:
        emit('game_start', {'your_color': 'Beyaz', 'room_id': rid}, to=opp)

    print(f'[Room {rid}] {request.sid[:8]} joined — game starting')


@socketio.on('make_move')
def handle_make_move(data: dict):
    """Relay a board move to the opponent."""
    rid = data.get('room_id')
    if rid not in rooms:
        return
    opp = other_player(rooms[rid], request.sid)
    if opp:
        emit('opponent_move', {'from': data['from'], 'to': data['to']}, to=opp)


@socketio.on('pie_decision')
def handle_pie_decision(data: dict):
    """Relay a Pie Rule decision (keep / swap) to the opponent."""
    rid = data.get('room_id')
    if rid not in rooms:
        return
    opp = other_player(rooms[rid], request.sid)
    if opp:
        emit('opponent_pie', {'decision': data['decision']}, to=opp)


@socketio.on('disconnect')
def handle_disconnect():
    """Clean up the room and notify the waiting opponent."""
    for rid, room in list(rooms.items()):
        if request.sid in room['players']:
            opp = other_player(room, request.sid)
            if opp:
                emit('opponent_disconnected', {}, to=opp)
            del rooms[rid]
            print(f'[Room {rid}] closed — {request.sid[:8]} disconnected')
            break


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
