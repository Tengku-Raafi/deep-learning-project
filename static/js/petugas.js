let lastIds = new Set();

async function loadAntrian() {
    try {
        const response = await fetch('/api/permohonan/list');
        const data = await response.json();
        renderTabel(data);
        updateStats(data);
    } catch (err) {
        console.error('Gagal load antrian:', err);
    }
}

function renderTabel(data) {
    const tbody = document.getElementById('tabel-body');
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Belum ada antrian hari ini</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(item => {
        const isBaru = !lastIds.has(item.id);
        const rowClass = isBaru && lastIds.size > 0 ? 'row-new' : '';
        const waktu = new Date(item.waktu_daftar).toLocaleTimeString('id-ID', {
            hour: '2-digit', minute: '2-digit'
        });
        
        return `
            <tr class="${rowClass}">
                <td class="nomor-cell">${item.nomor_antrian}</td>
                <td><span class="layanan-badge">${item.layanan}</span></td>
                <td>${item.deskripsi}</td>
                <td>${waktu}</td>
                <td><span class="status-badge status-${item.status}">${item.status.toUpperCase()}</span></td>
                <td>${renderAksi(item)}</td>
            </tr>
        `;
    }).join('');
    
    lastIds = new Set(data.map(item => item.id));
}

function renderAksi(item) {
    if (item.status === 'menunggu') {
        return `<button class="btn-aksi btn-layani" onclick="updateStatus(${item.id}, 'dilayani')">Layani</button>`;
    } else if (item.status === 'dilayani') {
        return `<button class="btn-aksi btn-selesai" onclick="updateStatus(${item.id}, 'selesai')">Selesai</button>`;
    }
    return '<span style="color:#95a5a6">-</span>';
}

function updateStats(data) {
    const menunggu = data.filter(d => d.status === 'menunggu').length;
    const dilayani = data.filter(d => d.status === 'dilayani').length;
    const selesai = data.filter(d => d.status === 'selesai').length;
    
    document.getElementById('total-antrian').textContent = data.length;
    document.getElementById('stat-menunggu').textContent = menunggu;
    document.getElementById('stat-dilayani').textContent = dilayani;
    document.getElementById('stat-selesai').textContent = selesai;
}

async function updateStatus(id, status) {
    try {
        await fetch(`/api/permohonan/${id}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        loadAntrian();
    } catch (err) {
        alert('Gagal update status: ' + err);
    }
}

function updateTanggal() {
    const now = new Date();
    document.getElementById('tanggal-now').textContent = 
        now.toLocaleDateString('id-ID', { 
            weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' 
        });
}

window.addEventListener('DOMContentLoaded', () => {
    updateTanggal();
    loadAntrian();
    setInterval(loadAntrian, 3000);
    setInterval(updateTanggal, 60000);
});