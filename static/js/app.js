// ============ STATE ============
let layananPilih = null;
let pollingInterval = null;
let kameraAktif = false;
let isProcessing = false;

const SYARAT_LAYANAN = {
    'KTP':  ['Fotokopi KK (1 lembar)', 'Surat pengantar RT/RW', 'Pas foto 3x4 background merah/biru', 'Fotokopi akta kelahiran'],
    'KK':   ['KK lama (asli)', 'KTP kepala keluarga', 'Surat pengantar RT/RW', 'Dokumen pendukung (akta nikah/kelahiran/kematian)'],
    'AKTA': ['Surat keterangan kelahiran dari bidan/RS', 'Fotokopi KTP orang tua', 'Fotokopi KK', 'Fotokopi buku nikah orang tua']
};

// ============ KAMERA — frame dikirim dari browser, hasil (dgn landmark
// + panel info) dikirim balik server dan ditampilkan lewat src <img>.
// Lihat script capture di user.html: window.__kameraReady / __kameraError /
// __kameraPaused dipakai buat sinkronisasi status di sini.
const KAMERA_IDS = ['webcam-img', 'webcam-img-konfirm', 'webcam-img-syarat'];

let _cekKameraTimer = null;

function tampilkanKamera(activeId) {
    KAMERA_IDS.forEach(id => {
        const img = document.getElementById(id);
        if (!img) return;
        img.style.display = (id === activeId) ? 'block' : 'none';
        // src tidak disentuh di sini — terus di-update otomatis oleh capture
        // loop di user.html selama __kameraPaused = false.
    });
}

function startKamera() {
    if (kameraAktif) return;
    const inner   = document.getElementById('kamera-inner');
    const overlay = document.getElementById('kamera-overlay');
    const errorEl = document.getElementById('kamera-error');

    window.__kameraPaused = false; // mulai kirim frame lagi

    if (_cekKameraTimer) clearInterval(_cekKameraTimer);

    const tandaiAktif = () => {
        document.getElementById('webcam-img').style.display = 'block';
        if (inner)   inner.style.display = 'none';
        if (overlay) overlay.classList.add('active');
        if (errorEl) errorEl.classList.remove('show');
        kameraAktif = true;
    };

    const tandaiError = () => {
        if (inner)   inner.style.display = 'none';
        if (overlay) overlay.classList.remove('active');
        if (errorEl) errorEl.classList.add('show');
        kameraAktif = false;
    };

    if (window.__kameraReady) {
        tandaiAktif();
        return;
    }
    if (window.__kameraError) {
        tandaiError();
        return;
    }

    // Belum ada frame pertama — tampilkan loading, cek ulang tiap 300ms
    // (maksimal ~10 detik) sampai frame pertama datang atau error muncul.
    if (inner)   inner.style.display = 'flex';
    if (overlay) overlay.classList.remove('active');

    let percobaan = 0;
    _cekKameraTimer = setInterval(() => {
        percobaan++;
        if (window.__kameraReady) {
            clearInterval(_cekKameraTimer);
            tandaiAktif();
        } else if (window.__kameraError || percobaan > 33) {
            clearInterval(_cekKameraTimer);
            tandaiError();
        }
    }, 300);
}

function stopKamera() {
    if (_cekKameraTimer) { clearInterval(_cekKameraTimer); _cekKameraTimer = null; }
    window.__kameraPaused = true; // hemat resource & bandwidth saat tidak dibutuhkan

    KAMERA_IDS.forEach(id => {
        const img = document.getElementById(id);
        if (img) img.style.display = 'none';
    });
    const inner   = document.getElementById('kamera-inner');
    const overlay = document.getElementById('kamera-overlay');
    if (inner)   inner.style.display = 'flex';
    if (overlay) overlay.classList.remove('active');
    kameraAktif = false;
}

// ============ NAVIGASI TAHAP ============
function nextTahap(tahapId) {
    document.querySelectorAll('.user-stage').forEach(t => t.classList.remove('active'));
    document.getElementById(`tahap-${tahapId}`).classList.add('active');
    if (window.lucide) lucide.createIcons();

    if (tahapId === 'deteksi') {
        startKamera();
        tampilkanKamera('webcam-img');
        startPolling();
    } else if (tahapId === 'konfirmasi') {
        window.__kameraPaused = false;
        tampilkanKamera('webcam-img-konfirm');
    } else if (tahapId === 'syarat') {
        window.__kameraPaused = false;
        tampilkanKamera('webcam-img-syarat');
    } else {
        stopPolling();
        stopKamera();
    }
}

// ============ POLLING ============
function startPolling() {
    stopPolling();
    pollingInterval = setInterval(pollDeteksi, 500);
}

function stopPolling() {
    if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
}

async function resetDeteksi() {
    try { await fetch('/api/deteksi/reset', { method: 'POST' }); } catch(e) {}
}

async function pollDeteksi() {
    if (isProcessing) return;
    try {
        const res  = await fetch('/api/deteksi/state');
        const data = await res.json();

        const bar = document.getElementById('conf-bar');
        const val = document.getElementById('conf-val');
        if (bar) bar.style.width = data.confidence + '%';
        if (val) val.textContent  = data.confidence + '%';

        if (data.action) {
            isProcessing = true;
            stopPolling();
            await resetDeteksi();

            const tahapAktif = document.querySelector('.user-stage.active');
            if (!tahapAktif) { isProcessing = false; return; }
            const tahapId = tahapAktif.id.replace('tahap-', '');

            if (tahapId === 'deteksi') {
                if (['KTP', 'KK', 'AKTA'].includes(data.action)) {
                    await deteksiLayanan(data.action);
                } else {
                    isProcessing = false;
                    startPolling();
                }
            } else if (tahapId === 'konfirmasi') {
                if (data.action === 'YA')         await konfirmasiLayanan(true);
                else if (data.action === 'TIDAK') await konfirmasiLayanan(false);
                else { isProcessing = false; startPolling(); }
            } else if (tahapId === 'syarat') {
                if (data.action === 'YA')         await konfirmasiSyarat(true);
                else if (data.action === 'TIDAK') await konfirmasiSyarat(false);
                else { isProcessing = false; startPolling(); }
            } else {
                isProcessing = false;
            }
        }
    } catch(e) {}
}

// ============ TAHAP 1: Countdown ============
let countdownInterval;

function startCountdown() {
    let seconds = 30;
    const bar = document.getElementById('countdown-bar');
    clearInterval(countdownInterval);
    countdownInterval = setInterval(() => {
        seconds--;
        const el = document.getElementById('countdown');
        if (el)  el.textContent = seconds;
        if (bar) bar.style.width = (seconds / 30 * 100) + '%';
        if (seconds <= 0) {
            clearInterval(countdownInterval);
            nextTahap('deteksi');
        }
    }, 1000);
}

// ============ TAHAP 2: Deteksi Layanan ============
async function deteksiLayanan(layanan) {
    layananPilih = layanan;
    const elPilih = document.getElementById('layanan-pilih');
    if (elPilih) elPilih.textContent = layanan;
    const elBadge = document.getElementById('konfirm-badge-label');
    if (elBadge) elBadge.textContent = layanan;

    await resetDeteksi();
    nextTahap('konfirmasi');

    setTimeout(() => {
        isProcessing = false;
        startPolling();
    }, 500);
}

// ============ TAHAP 3: Konfirmasi Layanan ============
async function konfirmasiLayanan(ya) {
    stopPolling();
    await resetDeteksi();

    if (ya) {
        const elSyarat = document.getElementById('layanan-syarat');
        if (elSyarat) elSyarat.textContent = layananPilih;
        const list = document.getElementById('list-syarat');
        if (list) {
            list.innerHTML = '';
            SYARAT_LAYANAN[layananPilih].forEach((syarat, i) => {
                const li = document.createElement('li');
                li.className = 'syarat-item';
                li.innerHTML = `<div class="syarat-item-num">${i + 1}</div><span>${syarat}</span>`;
                list.appendChild(li);
            });
        }
        nextTahap('syarat');
        setTimeout(() => { isProcessing = false; startPolling(); }, 500);
    } else {
        const bar = document.getElementById('conf-bar');
        const val = document.getElementById('conf-val');
        if (bar) bar.style.width = '0%';
        if (val) val.textContent = '0%';
        nextTahap('deteksi');
        setTimeout(() => { isProcessing = false; startPolling(); }, 500);
    }
}

// ============ TAHAP 4: Konfirmasi Syarat ============
async function konfirmasiSyarat(lengkap) {
    stopPolling();
    await resetDeteksi();
    isProcessing = false;
    stopKamera();

    if (lengkap) {
        try {
            const response = await fetch('/api/permohonan/baru', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ layanan: layananPilih })
            });
            const data = await response.json();
            document.getElementById('struk-nomor').textContent     = data.nomor_antrian;
            document.getElementById('struk-deskripsi').textContent = data.deskripsi;
            document.getElementById('struk-waktu').textContent     = data.waktu;
            const badge = document.getElementById('struk-badge');
            if (badge) {
                badge.textContent = layananPilih;
                badge.className   = `struk-layanan-badge badge-${layananPilih}`;
            }
            nextTahap('struk');
        } catch(err) {
            alert('Gagal menyimpan permohonan: ' + err);
        }
    } else {
        nextTahap('tidak-lengkap');
    }
}

// ============ RESET ============
function resetSistem() {
    layananPilih = null;
    isProcessing = false;
    stopPolling();
    stopKamera();
    const el = document.getElementById('countdown');
    if (el) el.textContent = '30';
    const bar = document.getElementById('conf-bar');
    const val = document.getElementById('conf-val');
    if (bar) bar.style.width = '0%';
    if (val) val.textContent = '0%';
    const cdBar = document.getElementById('countdown-bar');
    if (cdBar) cdBar.style.width = '100%';
    resetDeteksi();
    nextTahap('welcome');
    startCountdown();
}

// ============ INIT ============
window.addEventListener('DOMContentLoaded', () => {
    startCountdown();
});