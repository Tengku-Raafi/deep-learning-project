from flask import Flask, render_template, jsonify, request, redirect, url_for, session, Response
from functools import wraps
import sqlite3
import os
import hashlib
from datetime import datetime, date, timezone, timedelta

app = Flask(__name__)
app.secret_key = 'ganti-secret-key-ini-buat-production-yaa'
DB_PATH = 'database/permohonan.db'

# Cegah browser cache halaman protected — back button tidak bisa bypass logout
@app.after_request
def no_cache(response):
    if request.path.startswith('/petugas') or request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']        = 'no-cache'
        response.headers['Expires']       = '0'
    return response

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

def waktu_wib():
    """Return waktu sekarang dalam format string WIB."""
    return datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')

# ============ DATABASE ============
def init_db():
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS permohonan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomor_antrian TEXT NOT NULL,
            layanan TEXT NOT NULL,
            deskripsi TEXT,
            status TEXT DEFAULT 'menunggu',
            waktu_daftar DATETIME DEFAULT CURRENT_TIMESTAMP,
            waktu_dilayani DATETIME
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS petugas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nama_lengkap TEXT NOT NULL,
            jabatan TEXT
        )
    ''')
    cur.execute("SELECT COUNT(*) FROM petugas")
    if cur.fetchone()[0] == 0:
        default_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cur.execute(
            "INSERT INTO petugas (username, password_hash, nama_lengkap, jabatan) VALUES (?, ?, ?, ?)",
            ("admin", default_pass, "Administrator Kelurahan", "Kepala Petugas")
        )
        print("Akun default dibuat: username=admin, password=admin123")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============ AUTH ============
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'petugas_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ============ NOMOR ANTRIAN ============
def generate_nomor_antrian():
    conn = get_db()
    count = conn.execute("""
        SELECT COUNT(*) FROM permohonan
        WHERE DATE(waktu_daftar) = DATE(?)
    """, (waktu_wib(),)).fetchone()[0]
    conn.close()
    return f"A{count + 1:03d}"

DESKRIPSI_LAYANAN = {
    'KTP':  'Permohonan KTP Elektronik',
    'KK':   'Permohonan Kartu Keluarga',
    'AKTA': 'Permohonan Akta Kelahiran',
}

# ============ PUBLIC PAGES ============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user')
def user_page():
    return render_template('user.html')

# ============ LOGIN ============
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            error = "Username dan password wajib diisi"
        else:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            conn = get_db()
            petugas = conn.execute(
                "SELECT * FROM petugas WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            ).fetchone()
            conn.close()
            if petugas:
                session['petugas_id'] = petugas['id']
                session['petugas_nama'] = petugas['nama_lengkap']
                session['petugas_jabatan'] = petugas['jabatan']
                return redirect(url_for('petugas_dashboard'))
            else:
                error = "Username atau password salah"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============ PROTECTED PAGES ============
@app.route('/petugas')
@login_required
def petugas_dashboard():
    return render_template('petugas_dashboard.html')

@app.route('/petugas/antrian')
@login_required
def petugas_antrian():
    return render_template('petugas_antrian.html')

@app.route('/petugas/laporan')
@login_required
def petugas_laporan():
    return render_template('petugas_laporan.html')

@app.route('/petugas/riwayat')
@login_required
def petugas_riwayat():
    return render_template('petugas_riwayat.html')

# ============ INFERENCE ROUTES ============
@app.route('/video_feed')
def video_feed():
    from inference import generate_frames
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/deteksi/state')
def deteksi_state():
    from inference import get_detection_state
    return jsonify(get_detection_state())

@app.route('/api/deteksi/reset', methods=['POST'])
def deteksi_reset():
    from inference import reset_detection
    reset_detection()
    return jsonify({'success': True})

# ============ PUBLIC API ============
@app.route('/api/permohonan/baru', methods=['POST'])
def buat_permohonan():
    data    = request.json
    layanan = data.get('layanan', '').upper()
    if layanan not in DESKRIPSI_LAYANAN:
        return jsonify({'error': 'Layanan tidak valid'}), 400

    nomor     = generate_nomor_antrian()
    deskripsi = DESKRIPSI_LAYANAN[layanan]
    now_wib   = waktu_wib()  # waktu WIB yang benar

    conn = get_db()
    cur  = conn.execute(
        "INSERT INTO permohonan (nomor_antrian, layanan, deskripsi, waktu_daftar) VALUES (?, ?, ?, ?)",
        (nomor, layanan, deskripsi, now_wib)
    )
    permohonan_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        'id':            permohonan_id,
        'nomor_antrian': nomor,
        'layanan':       layanan,
        'deskripsi':     deskripsi,
        'waktu':         datetime.now(WIB).strftime('%d %B %Y, %H:%M')
    })

# ============ PROTECTED API ============
@app.route('/api/permohonan/list')
@login_required
def list_permohonan():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM permohonan
        WHERE status IN ('menunggu', 'dilayani')
        AND DATE(waktu_daftar) = DATE(?)
        ORDER BY id ASC
    """, (waktu_wib(),)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/permohonan/riwayat')
@login_required
def riwayat_permohonan():
    conn = get_db()
    rows = conn.execute('SELECT * FROM permohonan ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/permohonan/<int:permohonan_id>/status', methods=['POST'])
@login_required
def update_status(permohonan_id):
    status_baru = request.json.get('status')
    if status_baru not in ['menunggu', 'dilayani', 'selesai']:
        return jsonify({'error': 'Status tidak valid'}), 400
    conn = get_db()
    if status_baru == 'dilayani':
        conn.execute(
            "UPDATE permohonan SET status = ?, waktu_dilayani = ? WHERE id = ?",
            (status_baru, waktu_wib(), permohonan_id)
        )
    else:
        conn.execute(
            "UPDATE permohonan SET status = ? WHERE id = ?",
            (status_baru, permohonan_id)
        )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/permohonan/<int:permohonan_id>/cancel', methods=['POST'])
@login_required
def cancel_permohonan(permohonan_id):
    conn = get_db()
    row = conn.execute("SELECT status FROM permohonan WHERE id = ?", (permohonan_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Permohonan tidak ditemukan'}), 404
    if row['status'] == 'selesai':
        conn.close()
        return jsonify({'error': 'Permohonan sudah selesai'}), 400
    conn.execute("UPDATE permohonan SET status = 'dibatalkan' WHERE id = ?", (permohonan_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/permohonan/<int:permohonan_id>/hapus', methods=['DELETE'])
@login_required
def hapus_permohonan(permohonan_id):
    conn = get_db()
    row = conn.execute("SELECT status FROM permohonan WHERE id = ?", (permohonan_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Permohonan tidak ditemukan'}), 404
    if row['status'] not in ['dibatalkan', 'selesai']:
        conn.close()
        return jsonify({'error': 'Hanya data selesai/dibatalkan yang bisa dihapus'}), 400
    conn.execute("DELETE FROM permohonan WHERE id = ?", (permohonan_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/stats')
@login_required
def stats():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM permohonan
        WHERE DATE(waktu_daftar) = DATE(?)
    """, (waktu_wib(),)).fetchall()
    conn.close()
    return jsonify({
        'total':      len(rows),
        'menunggu':   sum(1 for r in rows if r['status'] == 'menunggu'),
        'dilayani':   sum(1 for r in rows if r['status'] == 'dilayani'),
        'selesai':    sum(1 for r in rows if r['status'] == 'selesai'),
        'dibatalkan': sum(1 for r in rows if r['status'] == 'dibatalkan'),
        'per_layanan': {
            'KTP':  sum(1 for r in rows if r['layanan'] == 'KTP'),
            'KK':   sum(1 for r in rows if r['layanan'] == 'KK'),
            'AKTA': sum(1 for r in rows if r['layanan'] == 'AKTA'),
        }
    })

@app.route('/api/laporan/<int:tahun>/<int:bulan>')
@login_required
def laporan_bulanan(tahun, bulan):
    bulan_str = f"{tahun}-{bulan:02d}"
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM permohonan
        WHERE strftime('%Y-%m', waktu_daftar) = ?
        ORDER BY waktu_daftar ASC
    """, (bulan_str,)).fetchall()
    conn.close()
    data = [dict(row) for row in rows]
    summary = {
        'KTP':        sum(1 for d in data if d['layanan'] == 'KTP'),
        'KK':         sum(1 for d in data if d['layanan'] == 'KK'),
        'AKTA':       sum(1 for d in data if d['layanan'] == 'AKTA'),
        'total':      len(data),
        'selesai':    sum(1 for d in data if d['status'] == 'selesai'),
        'dibatalkan': sum(1 for d in data if d['status'] == 'dibatalkan'),
        'menunggu':   sum(1 for d in data if d['status'] == 'menunggu'),
    }
    return jsonify({'data': data, 'summary': summary})

@app.route('/api/me')
@login_required
def me():
    return jsonify({
        'nama':    session.get('petugas_nama'),
        'jabatan': session.get('petugas_jabatan')
    })

if __name__ == '__main__':
    init_db()
    try:
        from inference import load_lstm_model
        if load_lstm_model():
            print("Model LSTM berhasil dimuat!")
        else:
            print("WARNING: Model tidak ditemukan, mode simulasi aktif")
    except Exception as e:
        print(f"WARNING: Inference tidak tersedia: {e}")

    print("=" * 50)
    print("Server jalan di http://localhost:5000")
    print("Login: admin / admin123")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5000)