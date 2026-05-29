const API_BASE = 'http://127.0.0.1:3000';

function getToken() {
    return localStorage.getItem('token') || '';
}

function authHeaders(extra) {
    const headers = Object.assign({}, extra || {});
    const token = getToken();
    if (token) headers.Authorization = 'Bearer ' + token;
    return headers;
}

async function parseResponse(res) {
    let body = null;
    try {
        body = await res.json();
    } catch (e) {
        body = { success: false, message: '服务端返回格式不正确' };
    }
    if (!res.ok) {
        throw new Error(body.message || ('服务端响应异常：' + res.status));
    }
    return body;
}

async function apiGet(path) {
    const res = await fetch(API_BASE + path, {
        headers: authHeaders()
    });
    return parseResponse(res);
}

async function apiPost(path, body) {
    const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
    });
    return parseResponse(res);
}

async function apiPut(path, body) {
    const res = await fetch(API_BASE + path, {
        method: 'PUT',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body || {}),
    });
    return parseResponse(res);
}

async function apiDelete(path) {
    const res = await fetch(API_BASE + path, {
        method: 'DELETE',
        headers: authHeaders(),
    });
    return parseResponse(res);
}

function showToast(message, type) {
    type = type || 'success';
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 3000);
}

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatTime(value) {
    if (!value) return '-';
    return String(value).substring(0, 16).replace('T', ' ');
}

function statusText(status) {
    const map = {
        available: '在岸可派遣',
        pending: '待处理',
        at_sea: '出海中',
        inactive: '已停用',
        pending_owner: '待船东确认',
        confirmed: '已确认',
        onboard: '已上船',
        offboard: '已下船',
        cancelled: '已取消',
        open: '招聘中',
        matched: '已匹配',
        closed: '已关闭',
        approved: '审核通过',
        rejected: '审核拒绝',
        active: '启用',
        maintenance: '维护中',
    };
    return map[status] || status || '-';
}

function badge(status) {
    const classMap = {
        available: 'success',
        approved: 'success',
        active: 'success',
        open: 'success',
        at_sea: 'info',
        onboard: 'info',
        pending: 'warning',
        pending_owner: 'warning',
        confirmed: 'warning',
        matched: 'warning',
        maintenance: 'warning',
        inactive: 'muted',
        offboard: 'muted',
        closed: 'muted',
        cancelled: 'danger',
        rejected: 'danger',
    };
    return '<span class="badge badge-' + (classMap[status] || 'muted') + '">' +
        escapeHtml(statusText(status)) + '</span>';
}

function bar(value, max) {
    const width = max > 0 ? Math.round((value / max) * 100) : 0;
    return '<div class="bar"><span style="width:' + width + '%"></span></div>';
}

function requireLogin() {
    if (!getToken()) {
        window.location.href = 'index.html';
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}
