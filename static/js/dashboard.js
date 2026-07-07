// ============ DASHBOARD ============

async function loadDashboard() {
    try {
        const statsRes = await fetch('/api/stats');
        const stats = await statsRes.json();

        animateCounter('stat-total', stats.total);
        animateCounter('stat-menunggu', stats.menunggu);
        animateCounter('stat-dilayani', stats.dilayani);
        animateCounter('stat-selesai', stats.selesai);

        const maxLayanan = Math.max(
            stats.per_layanan.KTP,
            stats.per_layanan.KK,
            stats.per_layanan.AKTA,
            1
        );

        document.getElementById('layanan-ktp').textContent = stats.per_layanan.KTP;
        document.getElementById('layanan-kk').textContent = stats.per_layanan.KK;
        document.getElementById('layanan-akta').textContent = stats.per_layanan.AKTA;

        setTimeout(() => {
            document.getElementById('bar-ktp').style.width = (stats.per_layanan.KTP / maxLayanan * 100) + '%';
            document.getElementById('bar-kk').style.width  = (stats.per_layanan.KK  / maxLayanan * 100) + '%';
            document.getElementById('bar-akta').style.width = (stats.per_layanan.AKTA / maxLayanan * 100) + '%';
        }, 300);

        const listRes = await fetch('/api/permohonan/list');
        const list = await listRes.json();
        renderActiveList(list);

    } catch (err) {
        console.error('Error loading dashboard:', err);
    }
}

function animateCounter(elementId, target) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const current = parseInt(el.textContent) || 0;
    const steps = 30;
    const increment = (target - current) / steps;
    let step = 0;
    const timer = setInterval(() => {
        step++;
        el.textContent = Math.round(current + increment * step);
        if (step >= steps) { el.textContent = target; clearInterval(timer); }
    }, 800 / steps);
}

function renderActiveList(items) {
    const container = document.getElementById('active-list');
    if (!container) return;

    const aktif = items.filter(d => d.status !== 'selesai').slice(0, 5);

    if (aktif.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i data-lucide="inbox" style="width:28px;height:28px;stroke-width:1.25;display:block;margin:0 auto 8px;opacity:0.4;"></i>
                Tidak ada antrian aktif
            </div>`;
        if (window.lucide) lucide.createIcons();
        return;
    }

    container.innerHTML = aktif.map((item, i) => {
        const waktu = new Date(item.waktu_daftar).toLocaleTimeString('id-ID', {
            hour: '2-digit', minute: '2-digit'
        });
        return `
            <div class="active-item layanan-${item.layanan}" style="animation-delay:${i * 0.08}s">
                <span class="active-nomor">${item.nomor_antrian}</span>
                <div class="active-info">
                    <div class="active-layanan ${item.layanan}">${item.layanan}</div>
                    <div class="active-time">${waktu} · ${item.status}</div>
                </div>
                <span class="status-badge status-${item.status}">${item.status}</span>
            </div>`;
    }).join('');
}

function updatePageDate() {
    const el = document.getElementById('page-date');
    if (el) el.textContent = new Date().toLocaleDateString('id-ID', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
}

window.addEventListener('DOMContentLoaded', () => {
    updatePageDate();
    loadDashboard();
    setInterval(loadDashboard, 5000);
});