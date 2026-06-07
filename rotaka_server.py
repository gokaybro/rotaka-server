"""
Rotaka Multiplayer Platform — Flask + Flask-SocketIO
"""

import os, random, string, json
from datetime import datetime
from flask import (Flask, render_template, request, session,
                   redirect, url_for, jsonify, flash)
from flask_socketio import SocketIO, emit, join_room, leave_room
import db as DB

# ─── APP SETUP ───────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rotaka-dev-secret-change-me')

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading',
                    logger=False, engineio_logger=False)

DB.init_db()

# ─── GOOGLE OAUTH (optional — configure via env vars) ────────────────────────

GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
google_oauth = None

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        from authlib.integrations.flask_client import OAuth
        _oauth = OAuth(app)
        google_oauth = _oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
    except ImportError:
        pass

# ─── IN-MEMORY ROOM STATE ────────────────────────────────────────────────────
# rooms: { room_id: { players:[sid,..], user_ids:{sid:uid}, colors:{sid:color},
#                     notation:[], game_id:int|None, spectators:set() } }
rooms: dict = {}
active_games: list = []   # snapshot list for live-games API


def gen_room_id():
    while True:
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if rid not in rooms:
            return rid


def current_user():
    uid = session.get('user_id')
    return DB.get_user_by_id(uid) if uid else None


# ─── AUTH HELPERS ────────────────────────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Lütfen giriş yapın.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── PAGE ROUTES ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    user = current_user()
    live = _live_games_list()
    return render_template('index.html', user=user, live_games=live)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        u = DB.verify_password(username, password)
        if u:
            session['user_id'] = u['id']
            DB.touch_last_seen(u['id'])
            return redirect(url_for('index'))
        flash('Kullanıcı adı veya şifre hatalı.', 'error')
    return render_template('login.html', user=None,
                           google_available=bool(google_oauth))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if len(username) < 3:
            flash('Kullanıcı adı en az 3 karakter olmalı.', 'error')
        elif len(password) < 6:
            flash('Şifre en az 6 karakter olmalı.', 'error')
        else:
            u = DB.create_user(username, password=password)
            if u:
                session['user_id'] = u['id']
                return redirect(url_for('index'))
            flash('Bu kullanıcı adı zaten alınmış.', 'error')
    return render_template('register.html', user=None)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# Google OAuth
@app.route('/auth/google')
def auth_google():
    if not google_oauth:
        flash('Google girişi şu an aktif değil.', 'error')
        return redirect(url_for('login'))
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google_oauth.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def auth_google_callback():
    if not google_oauth:
        return redirect(url_for('login'))
    token = google_oauth.authorize_access_token()
    info  = token.get('userinfo') or google_oauth.userinfo()
    gid   = info['sub']
    email = info.get('email', '')
    name  = info.get('name', '').replace(' ', '_')[:20]

    u = DB.get_user_by_google(gid)
    if not u:
        # try existing email
        base = name or email.split('@')[0]
        username = base
        attempt  = 0
        while DB.get_user_by_username(username):
            attempt += 1
            username = f'{base}{attempt}'
        u = DB.create_user(username, google_id=gid, email=email)
    if u:
        session['user_id'] = u['id']
        DB.touch_last_seen(u['id'])
    return redirect(url_for('index'))


@app.route('/profile/<username>')
def profile(username):
    viewer = current_user()
    u = DB.get_user_by_username(username)
    if not u:
        flash('Kullanıcı bulunamadı.', 'error')
        return redirect(url_for('index'))
    stats  = DB.get_user_stats(u['id'])
    games  = DB.get_user_games(u['id'], limit=10)
    friends = DB.get_friends(u['id'])
    is_friend = viewer and DB.are_friends(viewer['id'], u['id']) if viewer else False
    rank   = DB.elo_to_rank(u['elo'])
    rcolor = DB.rank_color(u['elo'])
    return render_template('profile.html', user=viewer, profile_user=u,
                           stats=stats, games=games, friends=friends,
                           is_friend=is_friend, rank=rank, rank_color=rcolor)


@app.route('/vs-computer')
def vs_computer():
    user = current_user()
    return render_template('vs_computer.html', user=user)


@app.route('/spectate')
def spectate():
    user  = current_user()
    live  = _live_games_list()
    return render_template('spectate.html', user=user, live_games=live)


@app.route('/game/<room_id>')
def game_page(room_id):
    user = current_user()
    return render_template('game.html', user=user, room_id=room_id)


# ─── REST API ────────────────────────────────────────────────────────────────

@app.route('/api/me')
def api_me():
    u = current_user()
    if not u:
        return jsonify({'error': 'not_logged_in'}), 401
    return jsonify({'id': u['id'], 'username': u['username'], 'elo': u['elo'],
                    'language': u['language']})


@app.route('/api/language', methods=['POST'])
def api_language():
    u = current_user()
    lang = request.json.get('lang', 'tr')
    if lang not in ('tr', 'en'):
        return jsonify({'error': 'invalid'}), 400
    if u:
        DB.update_language(u['id'], lang)
    # also store in session for guests
    session['language'] = lang
    return jsonify({'ok': True})


@app.route('/api/live-games')
def api_live_games():
    return jsonify(_live_games_list())


@app.route('/api/friend/add', methods=['POST'])
@login_required
def api_friend_add():
    uid = session['user_id']
    target = DB.get_user_by_username(request.json.get('username', ''))
    if not target or target['id'] == uid:
        return jsonify({'error': 'invalid'}), 400
    ok = DB.send_friend_request(uid, target['id'])
    return jsonify({'ok': ok})


@app.route('/api/friend/accept', methods=['POST'])
@login_required
def api_friend_accept():
    uid = session['user_id']
    req_id = request.json.get('requester_id')
    DB.accept_friend_request(req_id, uid)
    return jsonify({'ok': True})


@app.route('/api/leaderboard')
def api_leaderboard():
    rows = DB.leaderboard(20)
    return jsonify([dict(r) for r in rows])


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _live_games_list():
    result = []
    for rid, room in rooms.items():
        if len(room['players']) == 2:
            uids = [room['user_ids'].get(s) for s in room['players']]
            names = []
            for uid in uids:
                if uid:
                    u = DB.get_user_by_id(uid)
                    names.append(u['username'] if u else '?')
                else:
                    names.append('Misafir')
            result.append({
                'room_id': rid,
                'white': names[0] if room['colors'].get(room['players'][0]) == 'Beyaz' else names[1],
                'black': names[1] if room['colors'].get(room['players'][0]) == 'Beyaz' else names[0],
                'moves': len(room.get('notation', [])),
            })
    return result


def _room_of(sid):
    for rid, room in rooms.items():
        if sid in room['players'] or sid in room.get('spectators', set()):
            return rid, room
    return None, None


def _broadcast_room(rid, event, data):
    """Emit to all players + spectators in a room."""
    socketio.emit(event, data, to=rid)


# ─── SOCKET.IO ───────────────────────────────────────────────────────────────

@socketio.on('create_room')
def handle_create_room():
    rid = gen_room_id()
    uid = session.get('user_id')
    rooms[rid] = {
        'players':    [request.sid],
        'user_ids':   {request.sid: uid},
        'colors':     {request.sid: 'Beyaz'},
        'notation':   [],
        'game_id':    None,
        'spectators': set(),
        'started_at': datetime.utcnow().isoformat(),
    }
    join_room(rid)
    emit('room_created', {'room_id': rid, 'your_color': 'Beyaz'})


@socketio.on('join_room_req')
def handle_join_room(data):
    rid = data.get('room_id', '').strip().upper()
    uid = session.get('user_id')

    if rid not in rooms:
        emit('join_error', {'msg': 'Oda bulunamadı.'});  return
    room = rooms[rid]
    if len(room['players']) >= 2:
        emit('join_error', {'msg': 'Bu oda dolu.'});     return
    if request.sid in room['players']:
        emit('join_error', {'msg': 'Zaten bu odadasın.'}); return

    room['players'].append(request.sid)
    room['user_ids'][request.sid] = uid
    room['colors'][request.sid]   = 'Siyah'
    join_room(rid)

    # Create game record in DB
    white_sid = room['players'][0]
    black_sid = request.sid
    w_uid = room['user_ids'].get(white_sid)
    b_uid = uid
    w_elo = DB.get_user_by_id(w_uid)['elo'] if w_uid else 1000
    b_elo = DB.get_user_by_id(b_uid)['elo'] if b_uid else 1000
    room['game_id'] = DB.create_game(rid, w_uid, b_uid, w_elo, b_elo)

    # Notify both
    emit('game_start', {'your_color': 'Siyah', 'room_id': rid})
    emit('game_start', {'your_color': 'Beyaz', 'room_id': rid}, to=white_sid)


@socketio.on('spectate_join')
def handle_spectate_join(data):
    rid = data.get('room_id', '').strip().upper()
    if rid not in rooms:
        emit('spectate_error', {'msg': 'Oda bulunamadı.'}); return
    room = rooms[rid]
    room['spectators'].add(request.sid)
    join_room(rid)
    # Send current notation so spectator can replay
    emit('spectate_state', {'notation': room.get('notation', [])})


@socketio.on('make_move')
def handle_make_move(data):
    rid = data.get('room_id')
    if rid not in rooms: return
    room = rooms[rid]
    room['notation'] = data.get('notation', room['notation'])
    mover_color = room['colors'].get(request.sid, 'Beyaz')
    # broadcast to WHOLE room (players + spectators see it)
    socketio.emit('game_move', {
        'from':        data['from'],
        'to':          data['to'],
        'mover_color': mover_color,
    }, to=rid)


@socketio.on('pie_decision')
def handle_pie_decision(data):
    rid = data.get('room_id')
    if rid not in rooms: return
    # broadcast to whole room
    socketio.emit('opponent_pie', {'decision': data['decision']}, to=rid)
    # on swap, flip the colors stored server-side
    if data['decision'] == 'swap':
        room = rooms[rid]
        room['colors'] = {
            sid: ('Siyah' if col == 'Beyaz' else 'Beyaz')
            for sid, col in room['colors'].items()
        }


@socketio.on('chat_message')
def handle_chat(data):
    rid = data.get('room_id')
    if rid not in rooms: return
    uid  = session.get('user_id')
    u    = DB.get_user_by_id(uid) if uid else None
    name = u['username'] if u else 'Misafir'
    text = data.get('text', '').strip()[:200]
    if not text: return
    game_id = rooms[rid].get('game_id')
    if game_id:
        DB.save_message(game_id, uid, name, text)
    socketio.emit('new_message', {
        'username': name,
        'text':     text,
        'ts':       datetime.utcnow().strftime('%H:%M'),
    }, to=rid)


@socketio.on('game_over')
def handle_game_over(data):
    rid = data.get('room_id')
    if rid not in rooms: return
    room = rooms[rid]

    winner    = data.get('winner')   # 'Beyaz', 'Siyah', 'draw'
    reason    = data.get('reason', '')
    notation  = json.dumps(data.get('notation', []))
    game_id   = room.get('game_id')

    if game_id:
        # Determine user IDs
        w_sid = next((s for s in room['players'] if room['colors'].get(s) == 'Beyaz'), None)
        b_sid = next((s for s in room['players'] if room['colors'].get(s) == 'Siyah'), None)
        w_uid = room['user_ids'].get(w_sid)
        b_uid = room['user_ids'].get(b_sid)
        w_row = DB.get_user_by_id(w_uid) if w_uid else None
        b_row = DB.get_user_by_id(b_uid) if b_uid else None
        w_elo = w_row['elo'] if w_row else 1000
        b_elo = b_row['elo'] if b_row else 1000

        if winner == 'Beyaz':
            w_new, b_new = DB.calc_elo(w_elo, b_elo)
        elif winner == 'Siyah':
            b_new, w_new = DB.calc_elo(b_elo, w_elo)
        else:
            w_new, b_new = DB.calc_elo(w_elo, b_elo, is_draw=True)

        DB.finish_game(game_id, winner, reason, notation, w_new, b_new)
        if w_uid: DB.update_elo(w_uid, w_new)
        if b_uid: DB.update_elo(b_uid, b_new)

        # Notify elo changes
        socketio.emit('elo_update', {
            'white_elo': w_new, 'black_elo': b_new,
            'white_delta': w_new - w_elo,
            'black_delta': b_new - b_elo,
        }, to=rid)

    del rooms[rid]


@socketio.on('disconnect')
def handle_disconnect():
    rid, room = _room_of(request.sid)
    if not rid: return
    if request.sid in room.get('spectators', set()):
        room['spectators'].discard(request.sid)
        leave_room(rid)
        return
    # It's a player — notify opponent
    socketio.emit('opponent_disconnected', {}, to=rid)
    del rooms[rid]


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
