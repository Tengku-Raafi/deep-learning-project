// ============ RIWAYAT ============

let currentFilter = 'semua';
let currentPage = 1;
const PER_PAGE = 10;
let allData = [];

async function loadRiwayat() {
    try {
        const res = await fetch('/api/permohonan/riwayat');
        // Backend sudah ORDER BY id DESC, jadi langsung pakai
        allData = await res.json();
        renderTabel();

        const countEl = document.getElementById('riwayat-count');
        if (countEl) countEl.textContent = `${allData.length} total record`;
    } catch (err) {
        console.error('Error load riwayat:', err);
    }
}

function getFiltered() {
    return currentFilter === 'semua'
        ? allData
        : allData.filter(d => d.status === currentFilter);
}

function renderTabel() {
    const tbody = document.getElementById('riwayat-body');
    if (!tbody) return;

    const filtered = getFiltered();
    const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));

    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * PER_PAGE;
    const pageData = filtered.slice(start, start + PER_PAGE);

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7" class="empty">
                <i data-lucide="inbox" style="width:20px;height:20px;stroke-width:1.5;display:block;margin:0 auto 8px;opacity:0.4;"></i>
                Tidak ada data
            </td></tr>`;
        renderPagination(0, 1);
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = pageData.map(item => {
        const waktuDaftar = new Date(item.waktu_daftar).toLocaleString('id-ID', {
            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
        });
        const waktuDilayani = item.waktu_dilayani
            ? new Date(item.waktu_dilayani).toLocaleString('id-ID', {
                day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
              })
            : '—';

        const bisaHapus = ['selesai', 'dibatalkan'].includes(item.status);
        const btnHapus = bisaHapus
            ? `<button class="btn-aksi" style="border-color:#CC0000;color:#CC0000;font-size:10px;"
                onclick="hapusPermanen(${item.id}, '${item.nomor_antrian}')">Hapus</button>`
            : '';

        return `
            <tr>
                <td class="nomor-cell">${item.nomor_antrian}</td>
                <td><span class="layanan-badge layanan-${item.layanan}">${item.layanan}</span></td>
                <td>${item.deskripsi}</td>
                <td>${waktuDaftar}</td>
                <td>${waktuDilayani}</td>
                <td><span class="status-badge status-${item.status}">${item.status}</span></td>
                <td>${btnHapus}</td>
            </tr>`;
    }).join('');

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
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function hapusPermanen(id, nomor) {
    const ok = await showConfirm({
        title: 'Hapus Data Permanen?',
        highlight: nomor,
        desc: 'Data akan <strong>dihapus selamanya</strong> dari database dan tidak bisa dipulihkan kembali.',
        type: 'danger',
        btnOk: 'Ya, Hapus Permanen',
        btnCancel: 'Batal',
    });
    if (!ok) return;

    try {
        const res = await fetch(`/api/permohonan/${id}/hapus`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            loadRiwayat();
        } else {
            await showConfirm({
                title: 'Gagal Menghapus',
                desc: data.error || 'Terjadi kesalahan.',
                type: 'danger',
                btnOk: 'Tutup',
                btnCancel: null,
            });
        }
    } catch (err) {
        console.error('Gagal hapus:', err);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    loadRiwayat();

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