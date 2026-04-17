/**
 * Configuration Manager Module
 *
 * Handles frontend configuration settings including:
 * - API settings
 * - Visualization settings
 * - Safety settings
 * - Local storage persistence
 */

class ConfigManager {
    constructor() {
        this.config = {
            api: {
                baseUrl: 'http://localhost:8000',
                pollingInterval: 100,
                worldStatePollingInterval: 200,
                connectionTimeout: 5000
            },
            visualization: {
                gridSize: 0.1,
                animationSpeed: 0.1,
                showLabels: true,
                showGrid: true
            },
            safety: {
                maxSpeed: 1.0,
                emergencyStopKey: 'Escape',
                confirmEmergency: false
            },
            display: {
                theme: 'dark',
                logLevel: 'info'
            }
        };

        this.defaultConfig = { ...this.config };
    }

    init() {
        this.cacheElements();
        this.loadConfig();
        this.setupEventListeners();
        this.applyConfig();
    }

    cacheElements() {
        this.elements = {
            apiUrl: document.getElementById('apiUrl'),
            pollingInterval: document.getElementById('pollingInterval'),
            gridSize: document.getElementById('gridSize'),
            animSpeed: document.getElementById('animSpeed'),
            maxSpeed: document.getElementById('maxSpeed'),
            emergencyKey: document.getElementById('emergencyKey'),
            saveConfigBtn: document.getElementById('saveConfigBtn')
        };
    }

    loadConfig() {
        try {
            const savedConfig = localStorage.getItem('robotDashboardConfig');
            if (savedConfig) {
                const parsed = JSON.parse(savedConfig);
                this.mergeConfig(parsed);
            }
        } catch (error) {
            console.warn('Failed to load config from localStorage:', error);
        }
    }

    saveConfig() {
        try {
            localStorage.setItem('robotDashboardConfig', JSON.stringify(this.config));
            return true;
        } catch (error) {
            console.error('Failed to save config:', error);
            return false;
        }
    }

    mergeConfig(newConfig) {
        // Deep merge configuration
        this.config = this.deepMerge(this.config, newConfig);
    }

    deepMerge(target, source) {
        const result = { ...target };
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this.deepMerge(target[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        return result;
    }

    setupEventListeners() {
        if (this.elements.saveConfigBtn) {
            this.elements.saveConfigBtn.addEventListener('click', () => {
                this.saveConfig();
                this.applyConfig();
                this.showSaveNotification();
            });
        }

        // Update config on input change
        this.elements.apiUrl?.addEventListener('change', (e) => {
            this.config.api.baseUrl = e.target.value;
        });

        this.elements.pollingInterval?.addEventListener('change', (e) => {
            this.config.api.pollingInterval = parseInt(e.target.value, 10);
        });

        this.elements.gridSize?.addEventListener('change', (e) => {
            this.config.visualization.gridSize = parseFloat(e.target.value);
        });

        this.elements.animSpeed?.addEventListener('input', (e) => {
            const speed = parseInt(e.target.value, 10);
            // Convert slider value (1-20) to animation speed (0.05-0.2)
            this.config.visualization.animationSpeed = speed / 100;
        });

        this.elements.maxSpeed?.addEventListener('change', (e) => {
            this.config.safety.maxSpeed = parseFloat(e.target.value);
        });
    }

    applyConfig() {
        // Apply API settings
        if (this.elements.apiUrl) {
            this.elements.apiUrl.value = this.config.api.baseUrl;
        }
        if (this.elements.pollingInterval) {
            this.elements.pollingInterval.value = this.config.api.pollingInterval;
        }

        // Apply visualization settings
        if (this.elements.gridSize) {
            this.elements.gridSize.value = this.config.visualization.gridSize;
        }
        if (this.elements.animSpeed) {
            this.elements.animSpeed.value = this.config.visualization.animationSpeed * 100;
        }

        // Apply safety settings
        if (this.elements.maxSpeed) {
            this.elements.maxSpeed.value = this.config.safety.maxSpeed;
        }
        if (this.elements.emergencyKey) {
            this.elements.emergencyKey.value = this.config.safety.emergencyStopKey;
        }
    }

    showSaveNotification() {
        const btn = this.elements.saveConfigBtn;
        if (!btn) return;

        const originalText = btn.textContent;
        btn.textContent = 'Saved!';
        btn.classList.add('saved');

        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('saved');
        }, 1500);
    }

    getConfig() {
        return { ...this.config };
    }

    getApiUrl() {
        return this.config.api.baseUrl;
    }

    getPollingInterval() {
        return this.config.api.pollingInterval;
    }

    getWorldStatePollingInterval() {
        return this.config.api.worldStatePollingInterval;
    }

    getVisualizationConfig() {
        return { ...this.config.visualization };
    }

    getSafetyConfig() {
        return { ...this.config.safety };
    }

    resetToDefaults() {
        this.config = { ...this.defaultConfig };
        this.applyConfig();
        this.saveConfig();
    }
}

// Export for use in other modules
window.ConfigManager = ConfigManager;
