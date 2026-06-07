"""
Rotaka — SQLite veritabanı katmanı
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get('DB_PATH', 'rotaka.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def init_db():
    with get_conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    UNIQUE NOT NULL,
            password_hash TEXT,
            google_id    TEXT    UNIQUE,
            email        TEXT    UNIQUE,
            elo          INTEGER NOT NULL DEFAULT 1000,
            language     TEXT    NOT NULL DEFAULT 'tr',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS friendships (
            requester_id INTEGER NOT NULL REFERENCES users(id),
            addressee_id INTEGER NOT NULL REFERENCES users(id),
            status       TEXT    NOT NULL DEFAULT 'pending',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (requester_id, addressee_id)
        );

        CREATE TABLE IF NOT EXISTS games (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id          TEXT,
            white_user_id    INTEGER REFERENCES users(id),
            black_user_id    INTEGER REFERENCES users(id),
            winner           TEXT,
            win_reason       TEXT,
            notation         TEXT,
            white_elo_before INTEGER,
            black_elo_before INTEGER,
            white_elo_after  INTEGER,
            black_elo_after  INTEGER,
            started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at         TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS game_messages (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id  INTEGER NOT NULL REFERENCES games(id),
            user_id  INTEGER REFERENCES users(id),
            username TEXT,
            content  TEXT    NOT NULL,
            sent_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)


# ─── USER ────────────────────────────────────────────────────────────────────

def create_user(username, password=None, google_id=None, email=None):
    ph = generate_password_hash(password) if password else None
    try:
        with get_conn() as c:
            c.execute(
                'INSERT INTO users (username, password_hash, google_id, email) VALUES (?,?,?,?)',
                (username, ph, google_id, email)
            )
            return c.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    except sqlite3.IntegrityError:
        return None


def get_user_by_id(uid):
    with get_conn() as c:
        return c.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()


def get_user_by_username(username):
    with get_conn() as c:
        return c.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()


def get_user_by_google(google_id):
    with get_conn() as c:
        return c.execute('SELECT * FROM users WHERE google_id=?', (google_id,)).fetchone()


def verify_password(username, password):
    u = get_user_by_username(username)
    if u and u['password_hash'] and check_password_hash(u['password_hash'], password):
        return u
    return None


def update_elo(uid, new_elo):
    with get_conn() as c:
        c.execute('UPDATE users SET elo=? WHERE id=?', (new_elo, uid))


def update_language(uid, lang):
    with get_conn() as c:
        c.execute('UPDATE users SET language=? WHERE id=?', (lang, uid))


def touch_last_seen(uid):
    with get_conn() as c:
        c.execute("UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE id=?", (uid,))


def leaderboard(limit=20):
    with get_conn() as c:
        return c.execute(
            'SELECT username, elo FROM users ORDER BY elo DESC LIMIT ?', (limit,)
        ).fetchall()


# ─── FRIENDSHIP ──────────────────────────────────────────────────────────────

def send_friend_request(requester_id, addressee_id):
    try:
        with get_conn() as c:
            c.execute(
                'INSERT INTO friendships (requester_id, addressee_id) VALUES (?,?)',
                (requester_id, addressee_id)
            )
            return True
    except sqlite3.IntegrityError:
        return False


def accept_friend_request(requester_id, addressee_id):
    with get_conn() as c:
        c.execute(
            "UPDATE friendships SET status='accepted' WHERE requester_id=? AND addressee_id=?",
            (requester_id, addressee_id)
        )


def get_friends(uid):
    with get_conn() as c:
        return c.execute("""
            SELECT u.id, u.username, u.elo, f.status,
                   CASE WHEN f.requester_id=? THEN 'sent' ELSE 'received' END AS direction
            FROM friendships f
            JOIN users u ON (
                CASE WHEN f.requester_id=? THEN f.addressee_id ELSE f.requester_id END = u.id
            )
            WHERE f.requester_id=? OR f.addressee_id=?
        """, (uid, uid, uid, uid)).fetchall()


def are_friends(uid1, uid2):
    with get_conn() as c:
        row = c.execute("""
            SELECT 1 FROM friendships
            WHERE status='accepted'
              AND ((requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?))
        """, (uid1, uid2, uid2, uid1)).fetchone()
        return row is not None


# ─── GAMES ───────────────────────────────────────────────────────────────────

def create_game(room_id, white_uid, black_uid, white_elo, black_elo):
    with get_conn() as c:
        c.execute("""
            INSERT INTO games (room_id, white_user_id, black_user_id,
                               white_elo_before, black_elo_before)
            VALUES (?,?,?,?,?)
        """, (room_id, white_uid, black_uid, white_elo, black_elo))
        return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def finish_game(game_id, winner, win_reason, notation,
                white_elo_after, black_elo_after):
    with get_conn() as c:
        c.execute("""
            UPDATE games SET winner=?, win_reason=?, notation=?,
                             white_elo_after=?, black_elo_after=?,
                             ended_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (winner, win_reason, notation, white_elo_after, black_elo_after, game_id))


def get_user_games(uid, limit=20):
    with get_conn() as c:
        return c.execute("""
            SELECT g.*,
                   wu.username AS white_username,
                   bu.username AS black_username
            FROM games g
            LEFT JOIN users wu ON g.white_user_id = wu.id
            LEFT JOIN users bu ON g.black_user_id = bu.id
            WHERE (g.white_user_id=? OR g.black_user_id=?)
              AND g.ended_at IS NOT NULL
            ORDER BY g.ended_at DESC
            LIMIT ?
        """, (uid, uid, limit)).fetchall()


def get_user_stats(uid):
    with get_conn() as c:
        row = c.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN (winner='Beyaz' AND white_user_id=?) OR (winner='Siyah' AND black_user_id=?) THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN (winner='Beyaz' AND black_user_id=?) OR (winner='Siyah' AND white_user_id=?) THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN winner='draw' THEN 1 ELSE 0 END) AS draws,
                SUM(CASE WHEN win_reason='infiltration' AND ((winner='Beyaz' AND white_user_id=?) OR (winner='Siyah' AND black_user_id=?)) THEN 1 ELSE 0 END) AS inf_wins,
                SUM(CASE WHEN win_reason='elimination' AND ((winner='Beyaz' AND white_user_id=?) OR (winner='Siyah' AND black_user_id=?)) THEN 1 ELSE 0 END) AS elim_wins
            FROM games
            WHERE (white_user_id=? OR black_user_id=?) AND ended_at IS NOT NULL
        """, (uid,)*10).fetchone()
        return dict(row) if row else {}


# ─── MESSAGES ────────────────────────────────────────────────────────────────

def save_message(game_id, user_id, username, content):
    with get_conn() as c:
        c.execute(
            'INSERT INTO game_messages (game_id, user_id, username, content) VALUES (?,?,?,?)',
            (game_id, user_id, username, content)
        )


def get_game_messages(game_id):
    with get_conn() as c:
        return c.execute(
            'SELECT username, content, sent_at FROM game_messages WHERE game_id=? ORDER BY sent_at',
            (game_id,)
        ).fetchall()


# ─── ELO ─────────────────────────────────────────────────────────────────────

def calc_elo(winner_elo: int, loser_elo: int, is_draw: bool = False, k: int = 32):
    exp_w = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    exp_l = 1 - exp_w
    if is_draw:
        dw = round(k * (0.5 - exp_w))
        dl = round(k * (0.5 - exp_l))
    else:
        dw = round(k * (1.0 - exp_w))
        dl = round(k * (0.0 - exp_l))
    return (
        max(100, winner_elo + dw),
        max(100, loser_elo + dl),
    )


def elo_to_rank(elo: int) -> str:
    if elo >= 1800: return 'Usta'
    if elo >= 1600: return 'Elmas'
    if elo >= 1400: return 'Platin'
    if elo >= 1200: return 'Altın'
    if elo >= 1000: return 'Gümüş'
    return 'Bronz'


def rank_color(elo: int) -> str:
    if elo >= 1800: return '#9b59b6'
    if elo >= 1600: return '#3498db'
    if elo >= 1400: return '#1abc9c'
    if elo >= 1200: return '#f0c040'
    if elo >= 1000: return '#95a5a6'
    return '#cd7f32'
