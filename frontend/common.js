// 统一的 API 基础地址
const API_BASE = 'http://localhost:3000';

// 通用 fetch 封装
async function apiGet(path) {
    const res = await fetch(API_BASE + path);
    if (!res.ok) throw new Error('服务器响应异常: ' + res.status);
    return res.json();
}

async function apiPost(path, body) {
    const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('服务器响应异常: ' + res.status);
    return res.json();
}

async function apiPut(path, body) {
    const res = await fetch(API_BASE + path, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('服务器响应异常: ' + res.status);
    return res.json();
}

async function apiDelete(path) {
    const res = await fetch(API_BASE + path, { method: 'DELETE' });
    if (!res.ok) throw new Error('服务器响应异常: ' + res.status);
    return res.json();
}

// Toast 提示
function showToast(message, type) {
    type = type || 'success';
    var el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 3000);
}

// 格式化时间
function formatTime(isoString) {
    if (!isoString) return '待定';
    return isoString.substring(0, 16).replace('T', ' ');
}
