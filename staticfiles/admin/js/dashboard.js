// dashboard.js - JavaScript Principal du Dashboard

class DashboardManager {
    constructor() {
        this.ws = null;
        this.charts = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.fallbackInterval = null;
        
        this.init();
    }
    
    init() {
        console.log('🚀 Initialisation du Dashboard...');
        
        // Essaie la connexion WebSocket
        this.connectWebSocket();
        
        // Fallback: Polling GraphQL si WebSocket échoue
        setTimeout(() => {
            if (this.ws === null || this.ws.readyState !== WebSocket.OPEN) {
                console.log('⚠️ WebSocket non disponible, utilisation du polling');
                this.startFallbackPolling();
            }
        }, 5000);
        
        // Initialise les charts
        this.initCharts();
        
        // Demande les données initiales
        this.requestInitialData();
    }
    
    // ============================================
    // WEBSOCKET MANAGEMENT
    // ============================================
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/dashboard/`;
        
        try {
            this.ws = new WebSocket(url);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket connecté');
                this.updateConnectionStatus(true);
                this.reconnectAttempts = 0;
                this.requestInitialData();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (e) {
                    console.error('Erreur parsing message:', e);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('❌ WebSocket erreur:', error);
                this.updateConnectionStatus(false);
            };
            
            this.ws.onclose = () => {
                console.log('❌ WebSocket fermé');
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Erreur WebSocket:', error);
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 Tentative de reconnexion ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
            setTimeout(() => this.connectWebSocket(), this.reconnectDelay);
        }
    }
    
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket non connecté');
        }
    }
    
    handleMessage(message) {
        const type = message.type;
        
        switch(type) {
            case 'initial_stats':
            case 'stats_update':
                this.updateStats(message.data);
                break;
            
            case 'dashboard_update':
                this.handleDashboardUpdate(message);
                break;
            
            case 'activities_update':
                this.updateActivityFeed(message.data);
                break;
            
            case 'chart_update':
                this.updateChart(message.chart_type, message.data);
                break;
            
            default:
                console.log('Message inconnu:', type);
        }
    }
    
    requestInitialData() {
        this.sendMessage({ type: 'request_stats' });
        this.sendMessage({ type: 'request_activities', limit: 20 });
        
        // Demande les données des charts
        const chartTypes = [
            'activity_timeline',
            'device_distribution',
            'notifications_timeline',
            'events_by_status'
        ];
        
        chartTypes.forEach(type => {
            this.sendMessage({
                type: 'request_chart_data',
                chart_type: type
            });
        });
    }
    
    // ============================================
    // STATS UPDATE
    // ============================================
    
    updateStats(data) {
        console.log('📊 Mise à jour des stats:', data);
        
        // Met à jour les KPI cards avec animation
        this.updateKPI('totalLocations', data.total_locations);
        this.updateKPI('locationsMonth', data.locations_this_month);
        
        this.updateKPI('totalEvents', data.total_events);
        this.updateKPI('upcomingEvents', data.upcoming_events);
        
        this.updateKPI('totalHikings', data.total_hikings);
        this.updateKPI('hikingsMonth', data.hikings_this_month);
        
        this.updateKPI('activeAds', data.active_ads);
        this.updateKPI('totalAds', data.total_ads);
        
        this.updateKPI('totalDevices', data.total_fcm_devices);
        this.updateKPI('iosDevices', data.ios_devices);
        this.updateKPI('androidDevices', data.android_devices);
        
        this.updateKPI('notificationsSent', data.notifications_sent_24h);
        document.getElementById('notificationsFailed').textContent = 
            `${data.notifications_failed_24h} échouées`;
        
        // Met à jour le timestamp
        const now = new Date();
        document.getElementById('lastUpdate').textContent = 
            now.toLocaleTimeString('fr-FR');
    }
    
    updateKPI(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            const oldValue = parseInt(element.textContent) || 0;
            const newValue = parseInt(value);
            
            // Animation de changement
            if (newValue !== oldValue) {
                element.style.transition = 'all 0.3s ease';
                element.style.color = newValue > oldValue ? '#10b981' : '#ef4444';
                
                element.textContent = newValue;
                
                setTimeout(() => {
                    element.style.color = '';
                }, 2000);
            } else {
                element.textContent = newValue;
            }
        }
    }
    
    handleDashboardUpdate(message) {
        console.log('🔔 Mise à jour du dashboard:', message);
        
        // Demande les stats mises à jour
        setTimeout(() => {
            this.sendMessage({ type: 'request_stats' });
        }, 500);
        
        // Ajoute à la feed d'activité
        this.sendMessage({ type: 'request_activities', limit: 20 });
    }
    
    // ============================================
    // ACTIVITY FEED
    // ============================================
    
    updateActivityFeed(activities) {
        const feed = document.getElementById('activityFeed');
        if (!feed) return;
        
        feed.innerHTML = activities.map(activity => {
            const timestamp = new Date(activity.timestamp);
            const timeAgo = this.formatTimeAgo(timestamp);
            const statusClass = activity.success ? 'success' : 'error';
            
            return `
                <div class="activity-item ${statusClass} fade-in">
                    <div class="flex items-start justify-between">
                        <div>
                            <p class="font-medium text-sm text-gray-900">
                                ${activity.type}
                            </p>
                            <p class="text-sm text-gray-600 mt-1">
                                ${activity.entity_name || activity.entity_type}
                            </p>
                        </div>
                        <span class="badge ${activity.success ? 'badge-success' : 'badge-danger'}">
                            ${activity.success ? '✓ Succès' : '✗ Erreur'}
                        </span>
                    </div>
                    <p class="activity-time mt-2">${timeAgo}</p>
                </div>
            `;
        }).join('');
    }
    
    formatTimeAgo(date) {
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (seconds < 60) return 'à l\'instant';
        if (minutes < 60) return `il y a ${minutes}m`;
        if (hours < 24) return `il y a ${hours}h`;
        return `il y a ${Math.floor(hours / 24)}j`;
    }
    
    // ============================================
    // CHARTS
    // ============================================
    
    initCharts() {
        // Chart.js defaults
        Chart.defaults.color = '#64748b';
        Chart.defaults.borderColor = '#e2e8f0';
        Chart.defaults.font.family = "'Inter', sans-serif";
        
        // Activity Chart (Line)
        this.charts.activity = new Chart(
            document.getElementById('activityChart').getContext('2d'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Activités',
                        data: [],
                        borderColor: '#0f766e',
                        backgroundColor: 'rgba(15, 118, 110, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#0f766e',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { drawBorder: false }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            }
        );
        
        // Device Chart (Doughnut)
        this.charts.device = new Chart(
            document.getElementById('deviceChart').getContext('2d'),
            {
                type: 'doughnut',
                data: {
                    labels: ['iOS', 'Android'],
                    datasets: [{
                        data: [0, 0],
                        backgroundColor: ['#0f766e', '#7c3aed'],
                        borderColor: '#fff',
                        borderWidth: 2,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { padding: 20 }
                        }
                    }
                }
            }
        );
        
        // Events Chart (Bar)
        this.charts.events = new Chart(
            document.getElementById('eventsChart').getContext('2d'),
            {
                type: 'bar',
                data: {
                    labels: ['À venir', 'En cours', 'Passés'],
                    datasets: [{
                        label: 'Events',
                        data: [0, 0, 0],
                        backgroundColor: [
                            '#7c3aed',
                            '#14b8a6',
                            '#94a3b8'
                        ],
                        borderRadius: 6,
                        borderSkipped: false,
                    }]
                },
                options: {
                    responsive: true,
                    indexAxis: 'x',
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { drawBorder: false }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            }
        );
        
        // Notifications Chart (Mixed)
        this.charts.notifications = new Chart(
            document.getElementById('notificationsChart').getContext('2d'),
            {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Envoyées',
                            data: [],
                            backgroundColor: '#10b981',
                            borderRadius: 4,
                        },
                        {
                            label: 'Échouées',
                            data: [],
                            backgroundColor: '#ef4444',
                            borderRadius: 4,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    stacked: false,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { drawBorder: false }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            }
        );
    }
    
    updateChart(chartType, data) {
        console.log(`📈 Mise à jour chart ${chartType}`, data);
        
        switch(chartType) {
            case 'activity_timeline':
                this.updateActivityChart(data);
                break;
            
            case 'device_distribution':
                this.updateDeviceChart(data);
                break;
            
            case 'notifications_timeline':
                this.updateNotificationsChart(data);
                break;
            
            case 'events_by_status':
                this.updateEventsChart(data);
                break;
        }
    }
    
    updateActivityChart(data) {
        const chart = this.charts.activity;
        if (!chart) return;
        
        chart.data.labels = data.map(d => d.date.split('-').slice(1).join('/'));
        chart.data.datasets[0].data = data.map(d => d.count);
        chart.update('none');
    }
    
    updateDeviceChart(data) {
        const chart = this.charts.device;
        if (!chart) return;
        
        chart.data.datasets[0].data = data.map(d => d.value);
        chart.update('none');
    }
    
    updateEventsChart(data) {
        const chart = this.charts.events;
        if (!chart) return;
        
        chart.data.datasets[0].data = data.map(d => d.value);
        chart.update('none');
    }
    
    updateNotificationsChart(data) {
        const chart = this.charts.notifications;
        if (!chart) return;
        
        chart.data.labels = data.map(d => d.hour);
        chart.data.datasets[0].data = data.map(d => d.sent);
        chart.data.datasets[1].data = data.map(d => d.failed);
        chart.update('none');
    }
    
    // ============================================
    // FALLBACK POLLING (si WebSocket échoue)
    // ============================================
    
    startFallbackPolling() {
        this.fallbackInterval = setInterval(() => {
            this.sendMessage({ type: 'request_stats' });
        }, 10000); // Polling tous les 10 secondes
    }
    
    // ============================================
    // UI HELPERS
    // ============================================
    
    updateConnectionStatus(connected) {
        const status = document.getElementById('connectionStatus');
        const text = document.getElementById('connectionText');
        
        if (connected) {
            status.classList.remove('disconnected');
            status.classList.add('connected');
            text.textContent = '✓ Connecté';
        } else {
            status.classList.remove('connected');
            status.classList.add('disconnected');
            text.textContent = '✗ Déconnecté (polling)';
        }
    }
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    new DashboardManager();
});

// Add missing CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);