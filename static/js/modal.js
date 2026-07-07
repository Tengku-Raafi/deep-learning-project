// ============================================================
// modal.js — Custom Confirm Modal
// Gantikan confirm() bawaan browser
//
// Cara pakai:
//   const ok = await showConfirm({ ... })
//   if (ok) { ... lakukan aksi ... }
// ============================================================

function showConfirm({
    title   = 'Konfirmasi',
    desc    = 'Apakah Anda yakin?',
    highlight = null,      // teks yang di-highlight (nomor antrian, dll)
    type    = 'warning',   // 'danger' | 'warning' | 'info'
    btnOk   = 'Ya, Lanjutkan',
    btnCancel = 'Batal',
} = {}) {
    return new Promise((resolve) => {

        const ICONS = {
            danger:  'alert-triangle',
            warning: 'help-circle',
            info:    'info',
        };

        const highlightHtml = highlight
            ? `<div class="modal-highlight">${highlight}</div>`
            : '';

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal-box">
                <div class="modal-icon-wrap">
                    <div class="modal-icon ${type}">
                        <i data-lucide="${ICONS[type] || 'help-circle'}"></i>
                    </div>
                </div>
                <div class="modal-body">
                    <div class="modal-title">${title}</div>
                    ${highlightHtml}
                    <div class="modal-desc">${desc}</div>
                </div>
                <div class="modal-actions">
                    <button class="modal-btn modal-btn-cancel" id="modal-cancel">${btnCancel}</button>
                    <button class="modal-btn modal-btn-confirm-${type}" id="modal-ok">${btnOk}</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        if (window.lucide) lucide.createIcons();

        function close(result) {
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.15s ease';
            setTimeout(() => {
                overlay.remove();
                resolve(result);
            }, 150);
        }

        overlay.querySelector('#modal-ok').addEventListener('click', () => close(true));
        overlay.querySelector('#modal-cancel').addEventListener('click', () => close(false));

        // Klik di luar modal = batal
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) close(false);
        });

        // ESC = batal
        const onKey = (e) => {
            if (e.key === 'Escape') { document.removeEventListener('keydown', onKey); close(false); }
            if (e.key === 'Enter')  { document.removeEventListener('keydown', onKey); close(true); }
        };
        document.addEventListener('keydown', onKey);
    });
}