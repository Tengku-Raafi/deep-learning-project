// ============ LAPORAN BULANAN ============

const NAMA_BULAN = ['Januari','Februari','Maret','April','Mei','Juni',
                    'Juli','Agustus','September','Oktober','November','Desember'];

function setupTahunDropdown() {
    const select = document.getElementById('filter-tahun');
    if (!select) return;
    const tahunSekarang = new Date().getFullYear();
    for (let t = tahunSekarang - 2; t <= tahunSekarang + 1; t++) {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        if (t === tahunSekarang) opt.selected = true;
        select.appendChild(opt);
    }
}

function setBulanDefault() {
    const el = document.getElementById('filter-bulan');
    if (el) el.value = new Date().getMonth() + 1;
}

async function loadLaporan() {
    const tahun = document.getElementById('filter-tahun').value;
    const bulan = document.getElementById('filter-bulan').value;

    const periodeEl = document.getElementById('laporan-periode');
    if (periodeEl) periodeEl.textContent = `Periode: ${NAMA_BULAN[parseInt(bulan) - 1]} ${tahun}`;

    try {
        const res = await fetch(`/api/laporan/${tahun}/${bulan}`);
        const result = await res.json();

        animateCount('sum-ktp',   result.summary.KTP);
        animateCount('sum-kk',    result.summary.KK);
        animateCount('sum-akta',  result.summary.AKTA);
        animateCount('sum-total', result.summary.total);

        renderTabel(result.data);
    } catch (err) {
        console.error('Error load laporan:', err);
    }
}

function animateCount(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const current = parseInt(el.textContent) || 0;
    const steps = 20;
    const inc = (target - current) / steps;
    let step = 0;
    const timer = setInterval(() => {
        step++;
        el.textContent = Math.round(current + inc * step);
        if (step >= steps) { el.textContent = target; clearInterval(timer); }
    }, 600 / steps);
}

function renderTabel(data) {
    const tbody = document.getElementById('laporan-body');
    if (!tbody) return;

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">Tidak ada data untuk periode ini</td></tr>';
        return;
    }

    tbody.innerHTML = data.map(item => {
        const waktu = new Date(item.waktu_daftar).toLocaleString('id-ID', {
            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
        });
        return `
            <tr>
                <td class="nomor-cell">${item.nomor_antrian}</td>
                <td><span class="layanan-badge layanan-${item.layanan}">${item.layanan}</span></td>
                <td>${item.deskripsi}</td>
                <td>${waktu}</td>
                <td><span class="status-badge status-${item.status}">${item.status}</span></td>
            </tr>`;
    }).join('');
}

window.addEventListener('DOMContentLoaded', () => {
    setupTahunDropdown();
    setBulanDefault();
    loadLaporan();

    const btn = document.getElementById('btn-tampilkan');
    if (btn) btn.addEventListener('click', loadLaporan);
});