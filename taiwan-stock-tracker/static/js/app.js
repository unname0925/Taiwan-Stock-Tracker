// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info', duration = 3000) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = `toast ${type}`;
  setTimeout(() => t.classList.add('hidden'), duration);
}

// ── Refresh ───────────────────────────────────────────────────────────────
async function refreshData() {
  const btn = document.getElementById('refreshBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon">⟳</span> 抓取中…';
  }
  showToast('正在向 Yahoo Finance 抓取資料…', 'info', 8000);

  try {
    const res  = await fetch('/api/refresh', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(`✓ 資料更新完成（${data.date}）`, 'success');
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast('抓取失敗，請稍後再試', 'error');
    }
  } catch (e) {
    showToast('網路錯誤：' + e.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span class="btn-icon">⟳</span> 重新抓取資料';
    }
  }
}
