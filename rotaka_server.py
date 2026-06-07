"""
Rotaka Multiplayer Platform — Flask + Flask-SocketIO
Oda yapısı uid-tabanlı: socket sid değişse bile oda yaşamaya devam eder.
"""

import os, random, string, json, secrets
from datetime import datetime
from flask import (Flask, render_template, request, session,
                   redirect, url_for, jsonify, flash)
from flask_socketio import SocketIO, emit, join_room, leave_room
import db as DB

# ─── APP ─────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rotaka-dev-secret-change-me')

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading',
                    logger=False, engineio_logger=False)

DB.init_db()

# ─── GOOGLE OAUTH (optional) ─────────────────────────────────────────────────

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

# ─── ROOM STATE ───────────────────────────────────────────────────────────────
#
# rooms[rid] = {
#   'uid_to_color': { token: 'Beyaz'|'Siyah' },
#   'color_to_uid': { 'Beyaz': token, 'Siyah': token },
#   'uid_to_dbid':  { token: int|None },      # real DB user id
#   'active_sids':  { sid: token },            # currently connected sockets
#   'notation':     [...],
#   'game_id':      int|None,
#   'spectators':   set(),
# }
#
rooms: dict = {}


def gen_room_id():
    while True:
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if rid not in rooms:
            return rid


def _player_token():
    """Unique token per browser session (works for both guests and logged-in users)."""
    if 'player_token' not in session:
        session['player_token'] = secrets.token_hex(16)
    return session['player_token']


def current_user():
    uid = session.get('user_id')
    return DB.get_user_by_id(uid) if uid else None


# ─── AUTH HELPERS ─────────────────────────────────────────────────────────────

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


@app.route('/auth/google')
def auth_google():
    if not google_oauth:
        flash('Google girişi aktif değil.', 'error')
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
    stats   = DB.get_user_stats(u['id'])
    games   = DB.get_user_games(u['id'], limit=10)
    friends = DB.get_friends(u['id'])
    is_friend = viewer and DB.are_friends(viewer['id'], u['id']) if viewer else False
    rank   = DB.elo_to_rank(u['elo'])
    rcolor = DB.rank_color(u['elo'])
    return render_template('profile.html', user=viewer, profile_user=u,
                           stats=stats, games=games, friends=friends,
                           is_friend=is_friend, rank=rank, rank_color=rcolor)


@app.route('/vs-computer')
def vs_computer():
    return render_template('vs_computer.html', user=current_user())


@app.route('/spectate')
def spectate():
    return render_template('spectate.html', user=current_user(),
                           live_games=_live_games_list())


@app.route('/game/<room_id>')
def game_page(room_id):
    return render_template('game.html', user=current_user(),
                           room_id=room_id.upper())


# ─── REST API ─────────────────────────────────────────────────────────────────

@app.route('/api/me')
def api_me():
    u = current_user()
    if not u:
        return jsonify({'error': 'not_logged_in'}), 401
    return jsonify({'id': u['id'], 'username': u['username'],
                    'elo': u['elo'], 'language': u['language']})


@app.route('/api/language', methods=['POST'])
def api_language():
    u = current_user()
    lang = request.json.get('lang', 'tr')
    if lang not in ('tr', 'en'):
        return jsonify({'error': 'invalid'}), 400
    if u:
        DB.update_language(u['id'], lang)
    session['language'] = lang
    return jsonify({'ok': True})


@app.route('/api/live-games')
def api_live_games():
    return jsonify(_live_games_list())


@app.route('/api/friend/add', methods=['POST'])
@login_required
def api_friend_add():
    uid    = session['user_id']
    target = DB.get_user_by_username(request.json.get('username', ''))
    if not target or target['id'] == uid:
        return jsonify({'error': 'invalid'}), 400
    ok = DB.send_friend_request(uid, target['id'])
    return jsonify({'ok': ok})


@app.route('/api/friend/accept', methods=['POST'])
@login_required
def api_friend_accept():
    DB.accept_friend_request(request.json.get('requester_id'), session['user_id'])
    return jsonify({'ok': True})


@app.route('/api/leaderboard')
def api_leaderboard():
    return jsonify([dict(r) for r in DB.leaderboard(20)])


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _live_games_list():
    result = []
    for rid, room in rooms.items():
        if len(room['uid_to_color']) == 2 and room.get('game_id'):
            names = {}
            for tok, col in room['uid_to_color'].items():
                db_id = room['uid_to_dbid'].get(tok)
                u = DB.get_user_by_id(db_id) if db_id else None
                names[col] = u['username'] if u else 'Misafir'
            result.append({
                'room_id': rid,
                'white':   names.get('Beyaz', '?'),
                'black':   names.get('Siyah', '?'),
                'moves':   len(room.get('notation', [])),
            })
    return result


def _room_of_sid(sid):
    for rid, room in rooms.items():
        if sid in room.get('active_sids', {}):
            return rid, room
        if sid in room.get('spectators', set()):
            return rid, room
    return None, None


def _sid_color(room, sid):
    tok = room['active_sids'].get(sid)
    return room['uid_to_color'].get(tok) if tok else None


# ─── SOCKET.IO ────────────────────────────────────────────────────────────────

@socketio.on('create_room')
def handle_create_room():
    rid   = gen_room_id()
    tok   = _player_token()
    db_id = session.get('user_id')
    rooms[rid] = {
        'uid_to_color': {tok: 'Beyaz'},
        'color_to_uid': {'Beyaz': tok},
        'uid_to_dbid':  {tok: db_id},
        'active_sids':  {request.sid: tok},
        'notation':     [],
        'game_id':      None,
        'spectators':   set(),
    }
    join_room(rid)
    emit('room_created', {'room_id': rid, 'your_color': 'Beyaz'})


@socketio.on('join_room_req')
def handle_join_room(data):
    rid   = data.get('room_id', '').strip().upper()
    tok   = _player_token()
    db_id = session.get('user_id')

    if rid not in rooms:
        emit('join_error', {'msg': 'Oda bulunamadı.'}); return
    room = rooms[rid]

    # Already in this room (rejoin case)?
    if tok in room['uid_to_color']:
        join_room(rid)
        room['active_sids'][request.sid] = tok
        emit('game_start', {'your_color': room['uid_to_color'][tok], 'room_id': rid})
        return

    if len(room['uid_to_color']) >= 2:
        emit('join_error', {'msg': 'Bu oda dolu.'}); return

    room['uid_to_color'][tok]    = 'Siyah'
    room['color_to_uid']['Siyah'] = tok
    room['uid_to_dbid'][tok]     = db_id
    room['active_sids'][request.sid] = tok
    join_room(rid)

    # Create game record
    w_tok  = room['color_to_uid']['Beyaz']
    w_dbid = room['uid_to_dbid'].get(w_tok)
    b_dbid = db_id
    w_elo  = DB.get_user_by_id(w_dbid)['elo'] if w_dbid else 1000
    b_elo  = DB.get_user_by_id(b_dbid)['elo'] if b_dbid else 1000
    room['game_id'] = DB.create_game(rid, w_dbid, b_dbid, w_elo, b_elo)

    emit('game_start', {'your_color': 'Siyah', 'room_id': rid})
    socketio.emit('game_start', {'your_color': 'Beyaz', 'room_id': rid}, to=rid)


@socketio.on('game_connect')
def handle_game_connect(data):
    """Called by game.html on socket connect to (re)join a room."""
    rid = data.get('room_id', '').strip().upper()
    tok = _player_token()

    if rid not in rooms:
        emit('join_error', {'msg': 'Oda bulunamadı. Lobiye dönün.'}); return
    room = rooms[rid]

    if tok not in room['uid_to_color']:
        emit('join_error', {'msg': 'Bu odada yetkiniz yok.'}); return

    color = room['uid_to_color'][tok]
    room['active_sids'][request.sid] = tok
    join_room(rid)

    # Send current game state to this player
    emit('game_start', {
        'your_color':  color,
        'room_id':     rid,
        'notation':    room.get('notation', []),
        'both_joined': len(room['uid_to_color']) == 2,
    })


@socketio.on('spectate_join')
def handle_spectate_join(data):
    rid = data.get('room_id', '').strip().upper()
    if rid not in rooms:
        emit('spectate_error', {'msg': 'Oda bulunamadı.'}); return
    room = rooms[rid]
    room['spectators'].add(request.sid)
    join_room(rid)
    emit('spectate_state', {'notation': room.get('notation', [])})


@socketio.on('make_move')
def handle_make_move(data):
    rid = data.get('room_id')
    if rid not in rooms: return
    room = rooms[rid]
    room['notation'] = data.get('notation', room['notation'])
    mover_color = _sid_color(room, request.sid) or 'Beyaz'
    socketio.emit('game_move', {
        'from':        data['from'],
        'to':          data['to'],
        'mover_color': mover_color,
    }, to=rid)


@socketio.on('pie_decision')
def handle_pie_decision(data):
    rid = data.get('room_id')
    if rid not in rooms: return
    socketio.emit('opponent_pie', {'decision': data['decision']}, to=rid)
    if data['decision'] == 'swap':
        room = rooms[rid]
        room['uid_to_color'] = {tok: ('Siyah' if col == 'Beyaz' else 'Beyaz')
                                 for tok, col in room['uid_to_color'].items()}
        room['color_to_uid'] = {col: tok for tok, col in room['uid_to_color'].items()}


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

    winner   = data.get('winner')
    reason   = data.get('reason', '')
    notation = json.dumps(data.get('notation', []))
    game_id  = room.get('game_id')

    if game_id:
        w_tok  = room['color_to_uid'].get('Beyaz')
        b_tok  = room['color_to_uid'].get('Siyah')
        w_dbid = room['uid_to_dbid'].get(w_tok)
        b_dbid = room['uid_to_dbid'].get(b_tok)
        w_row  = DB.get_user_by_id(w_dbid) if w_dbid else None
        b_row  = DB.get_user_by_id(b_dbid) if b_dbid else None
        w_elo  = w_row['elo'] if w_row else 1000
        b_elo  = b_row['elo'] if b_row else 1000

        if winner == 'Beyaz':
            w_new, b_new = DB.calc_elo(w_elo, b_elo)
        elif winner == 'Siyah':
            b_new, w_new = DB.calc_elo(b_elo, w_elo)
        else:
            w_new, b_new = DB.calc_elo(w_elo, b_elo, is_draw=True)

        DB.finish_game(game_id, winner, reason, notation, w_new, b_new)
        if w_dbid: DB.update_elo(w_dbid, w_new)
        if b_dbid: DB.update_elo(b_dbid, b_new)

        socketio.emit('elo_update', {
            'white_elo': w_new, 'black_elo': b_new,
            'white_delta': w_new - w_elo,
            'black_delta': b_new - b_elo,
        }, to=rid)

    del rooms[rid]


@socketio.on('disconnect')
def handle_disconnect():
    rid, room = _room_of_sid(request.sid)
    if not rid: return

    if request.sid in room.get('spectators', set()):
        room['spectators'].discard(request.sid)
        return

    # Remove socket from active_sids but KEEP the room alive for reconnection
    room['active_sids'].pop(request.sid, None)

    # If no active players remain AND game hasn't started, clean up
    if not room['active_sids'] and not room.get('spectators') and not room.get('game_id'):
        del rooms[rid]


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
