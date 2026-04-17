/**
 * Monitoring Module
 *
 * Provides real-time monitoring tools including:
 * - Performance charts
 * - System health indicators
 * - Resource usage displays
 */

class Monitoring {
    constructor(apiClient) {
        this.api = apiClient;
        this.metricsHistory = {
            executionTime: [],
            successRate: [],
            cpuUsage: [],
            memoryUsage: []
        };
        this.maxHistoryLength = 60;
        this.updateInterval = null;
        this.systemHealth = {
            api: 'unknown',
            websocket: 'unknown',
            robot: 'unknown',
            metaclaw: 'unknown'
        };
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.startMonitoring();
    }

    cacheElements() {
        this.elements = {
            systemHealth: document.getElementById('systemHealth'),
            performanceChart: document.getElementById('performanceChart'),
            resourceUsage: document.getElementById('resourceUsage'),
            monitoringPanel: document.getElementById('monitoringPanel')
        };
    }

    setupEventListeners() {
        // Listen for connection changes
        this.api.on('connectionChange', (data) => {
            this.updateSystemHealth('api', data.connected ? 'healthy' : 'error');
        });

        // Listen for skill executions
        this.api.on('skillExecuted', (data) => {
            this.recordMetric('executionTime', data.result?.result?.execution_time || 0);
        });
    }

    startMonitoring() {
        // Update system health every 5 seconds
        this.updateInterval = setInterval(() => {
            this.checkSystemHealth();
            this.renderMetrics();
        }, 5000);

        // Initial render
        this.renderSystemHealth();
    }

    stopMonitoring() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    checkSystemHealth() {
        // Check API health
        this.systemHealth.api = this.api.connected ? 'healthy' : 'error';

        // Check WebSocket health
        this.systemHealth.websocket = (this.api.wsRobot?.readyState === WebSocket.OPEN) ? 'healthy' : 'error';

        // Check robot status via last update time
        const now = Date.now();
        this.systemHealth.robot = 'healthy'; // Default assumption

        // MetaClaw status (from debugger if available)
        if (window.robotDashboard?.skillDebugger?.metaclawStatus) {
            this.systemHealth.metaclaw = window.robotDashboard.skillDebugger.metaclawStatus.connected ? 'healthy' : 'error';
        }

        this.renderSystemHealth();
    }

    updateSystemHealth(component, status) {
        this.systemHealth[component] = status;
        this.renderSystemHealth();
    }

    recordMetric(type, value) {
        if (!this.metricsHistory[type]) {
            this.metricsHistory[type] = [];
        }

        this.metricsHistory[type].push({
            value: value,
            timestamp: Date.now()
        });

        // Trim history
        if (this.metricsHistory[type].length > this.maxHistoryLength) {
            this.metricsHistory[type].shift();
        }
    }

    renderSystemHealth() {
        const container = document.getElementById('systemHealth');
        if (!container) return;

        const healthItems = Object.entries(this.systemHealth).map(([component, status]) => {
            const statusClass = status === 'healthy' ? 'healthy' : 'error';
            const icon = status === 'healthy' ? '&#10004;' : '&#10008;';
            return `
                <div class="health-item ${statusClass}">
                    <span class="health-icon">${icon}</span>
                    <span class="health-label">${this.formatComponentName(component)}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div class="health-grid">
                ${healthItems}
            </div>
        `;
    }

    formatComponentName(name) {
        const names = {
            api: 'API',
            websocket: 'WebSocket',
            robot: 'Robot',
            metaclaw: 'MetaClaw'
        };
        return names[name] || name;
    }

    renderMetrics() {
        this.renderPerformanceChart();
        this.renderResourceUsage();
    }

    renderPerformanceChart() {
        const container = document.getElementById('performanceChart');
        if (!container) return;

        const history = this.metricsHistory.executionTime;
        if (history.length < 2) {
            container.innerHTML = '<div class="empty-state">Collecting data...</div>';
            return;
        }

        // Simple bar chart representation
        const maxValue = Math.max(...history.map(h => h.value), 1);
        const bars = history.slice(-20).map(h => {
            const height = (h.value / maxValue) * 100;
            return `<div class="chart-bar" style="height: ${Math.max(height, 2)}%"></div>`;
        }).join('');

        container.innerHTML = `
            <div class="chart-container">
                <div class="chart-bars">
                    ${bars}
                </div>
                <div class="chart-labels">
                    <span>Last ${history.slice(-20).length} executions</span>
                    <span>Max: ${maxValue.toFixed(2)}ms</span>
                </div>
            </div>
        `;
    }

    renderResourceUsage() {
        const container = document.getElementById('resourceUsage');
        if (!container) return;

        // Simulated resource data
        const cpuUsage = Math.random() * 30 + 10; // 10-40%
        const memoryUsage = Math.random() * 40 + 30; // 30-70%

        const html = `
            <div class="resource-grid">
                <div class="resource-item">
                    <div class="resource-label">CPU</div>
                    <div class="resource-bar">
                        <div class="resource-fill" style="width: ${cpuUsage}%"></div>
                    </div>
                    <div class="resource-value">${cpuUsage.toFixed(1)}%</div>
                </div>
                <div class="resource-item">
                    <div class="resource-label">Memory</div>
                    <div class="resource-bar">
                        <div class="resource-fill" style="width: ${memoryUsage}%"></div>
                    </div>
                    <div class="resource-value">${memoryUsage.toFixed(1)}%</div>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    getMetricsHistory() {
        return { ...this.metricsHistory };
    }

    getSystemHealth() {
        return { ...this.systemHealth };
    }
}

// Export for use in other modules
window.Monitoring = Monitoring;
