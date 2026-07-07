// ============ ANTRIAN AKTIF ============

let lastIds = new Set();
let currentFilter = 'semua';
let currentPage = 1;
const PER_PAGE = 10;
let allData = [];

async function loadAntrian() {
    try {
        const res = await fetch('/api/permohonan/list');
        const data = await res.json();
        // Descending — terbaru di atas
        allData = data.reverse();
        renderTabel();
    } catch (err) {
        console.error('Error load antrian:', err);
    }
}

function getFiltered() {
    return currentFilter === 'semua'
        ? allData
        : allData.filter(d => d.layanan === currentFilter);
}

function renderTabel() {
    const tbody = document.getElementById('tabel-body');
    if (!tbody) return;

    const filtered = getFiltered();
    const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));

    // Clamp currentPage
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * PER_PAGE;
    const pageData = filtered.slice(start, start + PER_PAGE);

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6" class="empty">
                <i data-lucide="inbox" style="width:20px;height:20px;stroke-width:1.5;display:block;margin:0 auto 8px;opacity:0.4;"></i>
                Tidak ada antrian ${currentFilter !== 'semua' ? currentFilter : 'hari ini'}
            </td></tr>`;
        renderPagination(0, 1);
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = pageData.map(item => {
        const isBaru = !lastIds.has(item.id);
        const rowClass = isBaru && lastIds.size > 0 ? 'row-new' : '';
        const waktu = new Date(item.waktu_daftar).toLocaleTimeString('id-ID', {
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
        return `
            <tr class="${rowClass}">
                <td class="nomor-cell">${item.nomor_antrian}</td>
                <td><span class="layanan-badge layanan-${item.layanan}">${item.layanan}</span></td>
                <td>${item.deskripsi}</td>
                <td>${waktu}</td>
                <td><span class="status-badge status-${item.status}">${item.status}</span></td>
                <td style="display:flex;gap:6px;flex-wrap:wrap;">${renderAksi(item)}</td>
            </tr>`;
    }).join('');

    lastIds = new Set(allData.map(item => item.id));
    renderPagination(filtered.length, totalPages);
    if (window.lucide) lucide.createIcons();
}

function renderPagination(total, totalPages) {
    let wrap = document.getElementById('pagination-wrap');
    if (!wrap) {
        wrap = document.createElement('div');
        wrap.id = 'pagination-wrap';
        wrap.style.cssText = `
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 24px; border-top: 1px solid #F1F3F5;
            background: #FAFAFA; flex-wrap: wrap; gap: 10px;
        `;
        document.querySelector('.tabel-wrapper').appendChild(wrap);
    }

    const from = total === 0 ? 0 : (currentPage - 1) * PER_PAGE + 1;
    const to   = Math.min(currentPage * PER_PAGE, total);

    // Buat nomor halaman yang ditampilkan
    let pages = [];
    if (totalPages <= 5) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        pages = [1];
        if (currentPage > 3) pages.push('...');
        for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
            pages.push(i);
        }
        if (currentPage < totalPages - 2) pages.push('...');
        pages.push(totalPages);
    }

    wrap.innerHTML = `
        <span style="font-size:12px;color:#6B7280;">
            Menampilkan <strong>${from}–${to}</strong> dari <strong>${total}</strong> data
        </span>
        <div style="display:flex;align-items:center;gap:4px;">
            <button onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}
                style="${btnPageStyle(false, currentPage === 1)}">
                <i data-lucide="chevron-left" style="width:14px;height:14px;stroke-width:2.5;"></i>
            </button>
            ${pages.map(p => p === '...'
                ? `<span style="padding:0 4px;color:#9CA3AF;font-size:13px;">…</span>`
                : `<button onclick="changePage(${p})" style="${btnPageStyle(p === currentPage, false)}">${p}</button>`
            ).join('')}
            <button onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}
                style="${btnPageStyle(false, currentPage === totalPages)}">
                <i data-lucide="chevron-right" style="width:14px;height:14px;stroke-width:2.5;"></i>
            </button>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

function btnPageStyle(active, disabled) {
    const base = `
        width:32px; height:32px; border-radius:6px; border:1px solid;
        font-size:12px; font-weight:600; cursor:pointer; font-family:inherit;
        display:inline-flex; align-items:center; justify-content:center;
        transition: all 0.15s;
    `;
    if (active)   return base + 'background:#002B7A;color:#fff;border-color:#002B7A;';
    if (disabled) return base + 'background:#F1F3F5;color:#CDD0D5;border-color:#E2E5E9;cursor:not-allowed;';
    return base + 'background:#fff;color:#454B56;border-color:#E2E5E9;';
}

function changePage(page) {
    const filtered = getFiltered();
    const totalPages = Math.ceil(filtered.length / PER_PAGE);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderTabel();
}

function renderAksi(item) {
    let html = '';
    if (item.status === 'menunggu') {
        html += `<button class="btn-aksi btn-layani" onclick="updateStatus(${item.id}, 'dilayani')">Layani</button>`;
        html += `<button class="btn-aksi" style="border-color:#CC0000;color:#CC0000;" onclick="cancelPermohonan(${item.id}, '${item.nomor_antrian}')">Batal</button>`;
    } else if (item.status === 'dilayani') {
        html += `<button class="btn-aksi btn-selesai-act" onclick="updateStatus(${item.id}, 'selesai')">Selesai</button>`;
    }
    return html || '<span style="color:var(--gray400)">—</span>';
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
        console.error('Gagal update status:', err);
    }
}

async function cancelPermohonan(id, nomor) {
    const ok = await showConfirm({
        title: 'Batalkan Permohonan?',
        highlight: nomor,
        desc: 'Data tetap tersimpan di riwayat sebagai <strong>dibatalkan</strong>. Tindakan ini tidak bisa diurungkan.',
        type: 'warning',
        btnOk: 'Ya, Batalkan',
        btnCancel: 'Kembali',
    });
    if (!ok) return;

    try {
        const res = await fetch(`/api/permohonan/${id}/cancel`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            loadAntrian();
        } else {
            await showConfirm({
                title: 'Gagal Membatalkan',
                desc: data.error || 'Terjadi kesalahan.',
                type: 'danger',
                btnOk: 'Tutup',
                btnCancel: null,
            });
        }
    } catch (err) {
        console.error('Gagal cancel:', err);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    loadAntrian();
    setInterval(loadAntrian, 3000);

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            currentPage = 1;
            renderTabel();
        });
    });
});