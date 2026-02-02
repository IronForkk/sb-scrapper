/**
 * SB-Scrapper Analytics Dashboard - Dashboard JavaScript
 */

// Konfigürasyon
const CONFIG = {
    refreshInterval: 5000,  // 5 saniye
    defaultLimit: 100,
    apiBaseUrl: '/api'
};

// Durum değişkenleri
let currentLevel = 'ALL';
let autoRefreshEnabled = true;
let refreshTimer = null;

// DOM elementleri
const elements = {
    totalRequests: document.getElementById('totalRequests'),
    totalLogs: document.getElementById('totalLogs'),
    errorRate: document.getElementById('errorRate'),
    totalErrors: document.getElementById('totalErrors'),
    logsTableBody: document.getElementById('logsTableBody'),
    logCount: document.getElementById('logCount'),
    autoRefreshToggle: document.getElementById('autoRefreshToggle'),
    themeToggle: document.getElementById('themeToggle'),
    refreshBtn: document.getElementById('refreshBtn'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
    filterAll: document.getElementById('filterAll'),
    filterInfo: document.getElementById('filterInfo'),
    filterError: document.getElementById('filterError'),
    // Live metrics elements
    liveOperations: document.getElementById('liveOperations'),
    liveDuration: document.getElementById('liveDuration'),
    liveErrorRate: document.getElementById('liveErrorRate'),
    liveTimeRange: document.getElementById('liveTimeRange')
};

/**
 * İstatistikleri API'den çeker
 */
async function fetchStats() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/stats`);
        const result = await response.json();
        
        if (result.success) {
            renderStats(result.data);
        }
    } catch (error) {
        console.error('İstatistik çekme hatası:', error);
    }
}

/**
 * Logları API'den çeker
 */
async function fetchLogs(level = 'ALL', limit = CONFIG.defaultLimit) {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/logs?level=${level}&limit=${limit}`);
        const result = await response.json();
        
        if (result.success) {
            renderLogs(result.data);
            elements.logCount.textContent = `${result.count} kayıt`;
        }
    } catch (error) {
        console.error('Log çekme hatası:', error);
        showError('Loglar yüklenirken hata oluştu');
    }
}

/**
 * Canlı metrikleri API'den çeker
 */
async function fetchLiveMetrics() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/live-metrics`);
        const result = await response.json();
        
        if (result.success) {
            renderLiveMetrics(result.data);
        }
    } catch (error) {
        console.error('Canlı metrik çekme hatası:', error);
    }
}

/**
 * CSV export yapar
 */
async function exportCsv() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/export/csv`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `sb-scrapper-export-${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            console.error('CSV export hatası');
        }
    } catch (error) {
        console.error('CSV export hatası:', error);
    }
}

/**
 * İstatistikleri ekrana render eder
 */
function renderStats(stats) {
    // Sayıları formatla
    elements.totalRequests.textContent = formatNumber(stats.total_requests);
    elements.totalLogs.textContent = formatNumber(stats.total_logs);
    elements.totalErrors.textContent = formatNumber(stats.total_errors);
    elements.errorRate.textContent = `${stats.error_rate}%`;
    
    // Hata oranına göre renk belirle
    if (stats.error_rate > 20) {
        elements.errorRate.classList.add('text-danger');
        elements.errorRate.classList.remove('text-warning', 'text-success');
    } else if (stats.error_rate > 10) {
        elements.errorRate.classList.add('text-warning');
        elements.errorRate.classList.remove('text-danger', 'text-success');
    } else {
        elements.errorRate.classList.add('text-success');
        elements.errorRate.classList.remove('text-danger', 'text-warning');
    }
}

/**
 * Logları tabloya render eder
 */
function renderLogs(logs) {
    if (!logs || logs.length === 0) {
        elements.logsTableBody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center py-4 text-muted">
                    <i class="bi bi-inbox"></i>
                    <div class="mt-2">Kayıt bulunamadı</div>
                </td>
            </tr>
        `;
        return;
    }
    
    elements.logsTableBody.innerHTML = logs.map(log => {
        const levelClass = getLevelClass(log.level);
        const timestamp = formatTimestamp(log.timestamp);
        const location = log.location || '-';
        const message = escapeHtml(log.message || '');
        
        return `
            <tr class="fade-in">
                <td class="log-timestamp">${timestamp}</td>
                <td><span class="${levelClass}">${log.level}</span></td>
                <td class="log-location">${escapeHtml(location)}</td>
                <td class="log-message" title="${message}">${message}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Log seviyesine göre CSS class döndürür
 */
function getLevelClass(level) {
    switch (level) {
        case 'ERROR':
            return 'log-level-error';
        case 'WARNING':
            return 'log-level-warning';
        case 'INFO':
        default:
            return 'log-level-info';
    }
}

/**
 * Zaman damgasını formatlar
 */
function formatTimestamp(timestamp) {
    try {
        // ISO formatı veya standart format olabilir
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) {
            return timestamp;
        }
        return date.toLocaleTimeString('tr-TR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch {
        return timestamp;
    }
}

/**
 * Sayıları formatlar (örn: 1.234)
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/**
 * HTML karakterlerini escape eder
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Canlı metrikleri render eder
 */
function renderLiveMetrics(metrics) {
    elements.liveOperations.textContent = formatNumber(metrics.total_operations);
    elements.liveDuration.textContent = metrics.avg_duration.toFixed(2);
    elements.liveErrorRate.textContent = metrics.error_rate.toFixed(1);
    elements.liveTimeRange.textContent = metrics.time_range_hours;
    
    // Hata oranına göre renk belirle
    if (metrics.error_rate > 20) {
        elements.liveErrorRate.classList.add('text-danger');
        elements.liveErrorRate.classList.remove('text-warning', 'text-success');
    } else if (metrics.error_rate > 10) {
        elements.liveErrorRate.classList.add('text-warning');
        elements.liveErrorRate.classList.remove('text-danger', 'text-success');
    } else {
        elements.liveErrorRate.classList.add('text-success');
        elements.liveErrorRate.classList.remove('text-danger', 'text-warning');
    }
}

/**
 * Hata mesajı gösterir
 */
function showError(message) {
    elements.logsTableBody.innerHTML = `
        <tr>
            <td colspan="4" class="text-center py-4 text-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <div class="mt-2">${escapeHtml(message)}</div>
            </td>
        </tr>
    `;
}
/**
 * Tüm verileri yeniler
 */
function refreshAll() {
    fetchStats();
    fetchLogs(currentLevel);
    fetchLiveMetrics();
    
    // Refresh butonuna animasyon ekle
    elements.refreshBtn.querySelector('i').classList.add('spin-animation');
    setTimeout(() => {
        elements.refreshBtn.querySelector('i').classList.remove('spin-animation');
    }, 500);
}


/**
 * Otomatik yenilemeyi başlatır/durdurur
 */
function setAutoRefresh(enabled) {
    autoRefreshEnabled = enabled;
    
    if (enabled) {
        refreshTimer = setInterval(refreshAll, CONFIG.refreshInterval);
    } else {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }
}

/**
 * Temayı değiştirir
 */
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    html.setAttribute('data-bs-theme', newTheme);
    
    // İkonu güncelle
    const icon = elements.themeToggle.querySelector('i');
    if (newTheme === 'dark') {
        icon.classList.remove('bi-sun');
        icon.classList.add('bi-moon-stars');
    } else {
        icon.classList.remove('bi-moon-stars');
        icon.classList.add('bi-sun');
    }
}

/**
 * Log filtresini değiştirir
 */
function setFilter(level) {
    currentLevel = level;
    
    // Buton durumlarını güncelle
    [elements.filterAll, elements.filterInfo, elements.filterError].forEach(btn => {
        btn.classList.remove('active');
    });
    
    if (level === 'ALL') elements.filterAll.classList.add('active');
    else if (level === 'INFO') elements.filterInfo.classList.add('active');
    else if (level === 'ERROR') elements.filterError.classList.add('active');
    
    // Logları yenile
    fetchLogs(level);
}
/**
 * Event listeners
 */
function initEventListeners() {
    // Auto refresh toggle
    elements.autoRefreshToggle.addEventListener('change', (e) => {
        setAutoRefresh(e.target.checked);
    });
    
    // Theme toggle
    elements.themeToggle.addEventListener('click', toggleTheme);
    
    // Refresh button
    elements.refreshBtn.addEventListener('click', refreshAll);
    
    // Export CSV button
    elements.exportCsvBtn.addEventListener('click', exportCsv);
    
    // Filter buttons
    elements.filterAll.addEventListener('click', () => setFilter('ALL'));
    elements.filterInfo.addEventListener('click', () => setFilter('INFO'));
    elements.filterError.addEventListener('click', () => setFilter('ERROR'));
}


/**
 * Uygulamayı başlatır
 */
function init() {
    initEventListeners();
    refreshAll();
    setAutoRefresh(true);
}

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', init);

// Spin animasyonu için CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .spin-animation {
        animation: spin 0.5s ease-in-out;
    }
`;
document.head.appendChild(style);
