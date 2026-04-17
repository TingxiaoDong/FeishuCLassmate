/**
 * Robot Control Dashboard Application
 *
 * Main application logic that ties together:
 * - API client for backend communication
 * - Workspace visualization
 * - UI state management
 * - Event handling
 */

class RobotDashboard {
    constructor() {
        this.api = new RobotAPIClient('http://localhost:8000');
        this.visualization = null;
        this.skillExecution = null;
        this.skillDebugger = null;
        this.configManager = null;
        this.monitoring = null;
        this.eventLogEntries = [];
        this.maxLogEntries = 50;

        // DOM elements cache
        this.elements = {};

        // Polling interval for status updates
        this.statusPollingInterval = null;
        this.worldStatePollingInterval = null;
    }

    async init() {
        console.log('Initializing Robot Control Dashboard...');

        // Cache DOM elements
        this.cacheElements();

        // Initialize visualization
        this.visualization = new WorkspaceVisualization('workspaceCanvas');

        // Initialize config manager
        this.configManager = new ConfigManager();
        this.configManager.init();

        // Initialize skill execution
        this.skillExecution = new SkillExecution(this.api);
        this.skillExecution.init();

        // Initialize skill debugger
        this.skillDebugger = new SkillDebugger(this.api);
        this.skillDebugger.init();

        // Initialize monitoring
        this.monitoring = new Monitoring(this.api);
        this.monitoring.init();

        // Setup event listeners
        this.setupEventListeners();

        // Setup API event handlers
        this.setupAPIHandlers();

        // Initialize UI state
        this.updateConnectionStatus('disconnected');

        // Log initialization
        this.addLogEntry('Dashboard initialized', 'success');

        // Show skills panel
        this.showSkillsPanel();

        // Show monitoring panel
        this.showMonitoringPanel();

        // Try to connect
        this.connect();
    }

    cacheElements() {
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            robotState: document.getElementById('robotState'),
            eeX: document.getElementById('eeX'),
            eeY: document.getElementById('eeY'),
            eeZ: document.getElementById('eeZ'),
            gripperWidth: document.getElementById('gripperWidth'),
            gripperForce: document.getElementById('gripperForce'),
            joints: {
                j1: document.getElementById('j1'),
                j2: document.getElementById('j2'),
                j3: document.getElementById('j3'),
                j4: document.getElementById('j4'),
                j5: document.getElementById('j5'),
                j6: document.getElementById('j6')
            },
            objectsList: document.getElementById('objectsList'),
            eventLog: document.getElementById('eventLog'),
            emergencyStop: document.getElementById('emergencyStop')
        };
    }

    setupEventListeners() {
        // Control buttons
        document.querySelectorAll('.control-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                if (action) {
                    this.handleControlAction(action);
                }
            });
        });

        // Emergency stop button
        if (this.elements.emergencyStop) {
            this.elements.emergencyStop.addEventListener('click', () => {
                this.handleEmergencyStop();
            });
        }

        // Window resize
        window.addEventListener('resize', () => {
            if (this.visualization) {
                this.visualization.resize();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.handleEmergencyStop();
            }
        });
    }

    setupAPIHandlers() {
        // Connection status changes
        this.api.on('connectionChange', (data) => {
            this.updateConnectionStatus(data.connected ? 'connected' : 'disconnected');
        });

        // World state updates
        this.api.on('worldState', (worldState) => {
            this.updateFromWorldState(worldState);
        });

        // Robot status updates
        this.api.on('robotStatus', (status) => {
            this.updateFromRobotStatus(status);
        });

        // Errors
        this.api.on('error', (error) => {
            this.addLogEntry(`Error: ${error.message}`, 'error');
        });

        // Command results
        this.api.on('commandResult', (result) => {
            this.handleCommandResult(result);
        });
    }

    async connect() {
        try {
            this.updateConnectionStatus('connecting');
            this.addLogEntry('Connecting to robot API...', 'warning');

            await this.api.connect();

            this.addLogEntry('Connected to robot API', 'success');
            this.startPolling();

        } catch (error) {
            console.error('Failed to connect:', error);
            this.addLogEntry('Connection failed - running in demo mode', 'error');

            // Start demo mode with simulated data
            this.startDemoMode();
        }
    }

    startPolling() {
        // Poll for robot status every 100ms
        this.statusPollingInterval = setInterval(() => {
            this.pollRobotStatus();
        }, 100);

        // Poll for world state every 200ms
        this.worldStatePollingInterval = setInterval(() => {
            this.pollWorldState();
        }, 200);
    }

    stopPolling() {
        if (this.statusPollingInterval) {
            clearInterval(this.statusPollingInterval);
            this.statusPollingInterval = null;
        }
        if (this.worldStatePollingInterval) {
            clearInterval(this.worldStatePollingInterval);
            this.worldStatePollingInterval = null;
        }
    }

    async pollRobotStatus() {
        try {
            const status = await this.api.getRobotStatus();
            this.updateFromRobotStatus(status);
        } catch (error) {
            // Silently handle polling errors
        }
    }

    async pollWorldState() {
        try {
            const worldState = await this.api.getWorldState();
            this.updateFromWorldState(worldState);
        } catch (error) {
            // Silently handle polling errors
        }
    }

    startDemoMode() {
        // Generate simulated data for demo/offline mode
        this.addLogEntry('Starting demo mode with simulated data', 'warning');

        // Demo robot state
        const demoState = {
            state: 'IDLE',
            position: { x: 0.1, y: 0.0, z: 0.2 },
            sensor_data: {},
            message: 'Demo mode'
        };

        // Demo world state
        const demoWorldState = {
            timestamp: Date.now() / 1000,
            robot: {
                joint_positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                end_effector_pose: { x: 0.1, y: 0.0, z: 0.2, rx: 0, ry: 0, rz: 0 },
                gripper_width: 0.0,
                gripper_force: 0.0
            },
            objects: [
                { id: 'obj1', type: 'block', pose: { x: 0.2, y: 0.15, z: 0 }, color: '#e74c3c', state: 'visible' },
                { id: 'obj2', type: 'block', pose: { x: -0.1, y: 0.2, z: 0 }, color: '#2ecc71', state: 'visible' }
            ],
            environment: {
                obstacles: [
                    { id: 'obs1', pose: { x: 0.3, y: -0.2, z: 0 }, shape: 'box', size: { x: 0.05, y: 0.05 } }
                ],
                workspace_bounds: { x_min: -0.5, x_max: 0.5, y_min: -0.5, y_max: 0.5, z_min: 0, z_max: 0.5 }
            }
        };

        // Initial update
        this.updateFromRobotStatus(demoState);
        this.updateFromWorldState(demoWorldState);

        // Simulate robot movement in demo mode
        let t = 0;
        this.demoInterval = setInterval(() => {
            t += 0.02;

            // Simulate moving robot
            const x = 0.1 + Math.sin(t) * 0.1;
            const y = Math.cos(t * 0.7) * 0.1;
            const z = 0.2 + Math.sin(t * 1.3) * 0.05;

            demoWorldState.robot.end_effector_pose.x = x;
            demoWorldState.robot.end_effector_pose.y = y;
            demoWorldState.robot.end_effector_pose.z = z;
            demoWorldState.robot.gripper_width = Math.max(0, Math.sin(t * 0.5) * 0.5);
            demoWorldState.timestamp = Date.now() / 1000;

            this.updateFromWorldState(demoWorldState);

            demoState.position = { x, y, z };
            this.updateFromRobotStatus(demoState);
        }, 50);
    }

    stopDemoMode() {
        if (this.demoInterval) {
            clearInterval(this.demoInterval);
            this.demoInterval = null;
        }
    }

    updateConnectionStatus(status) {
        const el = this.elements.connectionStatus;
        const textEl = el.querySelector('.status-text');

        el.classList.remove('connected', 'connecting', 'disconnected');
        el.classList.add(status);

        switch (status) {
            case 'connected':
                textEl.textContent = 'Connected';
                break;
            case 'connecting':
                textEl.textContent = 'Connecting...';
                break;
            case 'disconnected':
                textEl.textContent = 'Disconnected';
                break;
        }
    }

    updateFromRobotStatus(status) {
        // Update robot state
        if (this.elements.robotState) {
            this.elements.robotState.textContent = status.state || 'UNKNOWN';
            this.elements.robotState.className = 'status-value ' + this.getStateClass(status.state);
        }

        // Update end effector position
        if (status.position) {
            if (this.elements.eeX) this.elements.eeX.textContent = (status.position.x || 0).toFixed(3);
            if (this.elements.eeY) this.elements.eeY.textContent = (status.position.y || 0).toFixed(3);
            if (this.elements.eeZ) this.elements.eeZ.textContent = (status.position.z || 0).toFixed(3);
        }

        // Update gripper
        if (status.sensor_data && status.sensor_data.gripper) {
            if (this.elements.gripperWidth) {
                this.elements.gripperWidth.textContent = (status.sensor_data.gripper.width || 0).toFixed(3);
            }
            if (this.elements.gripperForce) {
                this.elements.gripperForce.textContent = (status.sensor_data.gripper.force || 0).toFixed(3);
            }
        }
    }

    updateFromWorldState(worldState) {
        // Update visualization
        if (this.visualization && worldState) {
            this.visualization.updateWorldState(worldState);
        }

        // Update joint positions
        if (worldState.robot && worldState.robot.joint_positions) {
            const joints = worldState.robot.joint_positions;
            const jointKeys = ['j1', 'j2', 'j3', 'j4', 'j5', 'j6'];
            jointKeys.forEach((key, i) => {
                if (this.elements.joints[key] && joints[i] !== undefined) {
                    this.elements.joints[key].textContent = joints[i].toFixed(3);
                }
            });
        }

        // Update gripper from world state
        if (worldState.robot) {
            if (this.elements.gripperWidth) {
                this.elements.gripperWidth.textContent = (worldState.robot.gripper_width || 0).toFixed(3);
            }
            if (this.elements.gripperForce) {
                this.elements.gripperForce.textContent = (worldState.robot.gripper_force || 0).toFixed(3);
            }
        }

        // Update objects list
        this.updateObjectsList(worldState.objects || []);
    }

    updateObjectsList(objects) {
        const container = this.elements.objectsList;

        if (objects.length === 0) {
            container.innerHTML = '<div class="empty-state">No objects detected</div>';
            return;
        }

        container.innerHTML = objects.map(obj => `
            <div class="object-card">
                <div class="object-color-indicator" style="background-color: ${obj.color || '#2ecc71'}"></div>
                <div class="object-info">
                    <h4>${obj.id}</h4>
                    <span>${obj.type} at (${obj.pose.x.toFixed(2)}, ${obj.pose.y.toFixed(2)}, ${obj.pose.z.toFixed(2)})</span>
                </div>
                <span class="object-state">${obj.state}</span>
            </div>
        `).join('');
    }

    handleControlAction(action) {
        this.addLogEntry(`Action: ${action}`, 'info');

        switch (action) {
            case 'move_x_plus':
                this.api.moveRelative(0.05, 0, 0).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'move_x_minus':
                this.api.moveRelative(-0.05, 0, 0).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'move_y_plus':
                this.api.moveRelative(0, 0.05, 0).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'move_y_minus':
                this.api.moveRelative(0, -0.05, 0).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'move_z_plus':
                this.api.moveRelative(0, 0, 0.05).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'move_z_minus':
                this.api.moveRelative(0, 0, -0.05).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'grip':
                this.api.grip(0.5, 0.0).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'release':
                this.api.release().catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'lift':
                this.api.lift(0.3).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'place':
                this.api.place(0, 0, 0.1).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
            case 'rotate':
                this.api.rotate(90).catch(e => this.addLogEntry(`Error: ${e.message}`, 'error'));
                break;
        }
    }

    async handleEmergencyStop() {
        this.addLogEntry('EMERGENCY STOP ACTIVATED', 'error');

        try {
            await this.api.emergencyStop();
        } catch (error) {
            this.addLogEntry(`Emergency stop failed: ${error.message}`, 'error');
        }

        // Visual feedback
        this.elements.emergencyStop.classList.add('active');
        setTimeout(() => {
            this.elements.emergencyStop.classList.remove('active');
        }, 500);
    }

    handleCommandResult(result) {
        if (result.status === 'completed') {
            this.addLogEntry(`Command ${result.command_id} completed`, 'success');
        } else if (result.status === 'error') {
            this.addLogEntry(`Command ${result.command_id} error: ${result.message}`, 'error');
        }
    }

    getStateClass(state) {
        switch (state) {
            case 'IDLE': return 'state-idle';
            case 'EXECUTING': return 'state-executing';
            case 'COMPLETED': return 'state-completed';
            case 'ERROR': return 'state-error';
            default: return '';
        }
    }

    addLogEntry(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();

        this.eventLogEntries.unshift({
            time: timestamp,
            message,
            type
        });

        // Limit entries
        if (this.eventLogEntries.length > this.maxLogEntries) {
            this.eventLogEntries.pop();
        }

        // Update UI
        this.renderEventLog();
    }

    showSkillsPanel() {
        const skillsPanel = document.getElementById('skillsPanel');
        if (skillsPanel) {
            skillsPanel.classList.add('visible');
        }
    }

    hideSkillsPanel() {
        const skillsPanel = document.getElementById('skillsPanel');
        if (skillsPanel) {
            skillsPanel.classList.remove('visible');
        }
    }

    showMonitoringPanel() {
        const monitoringPanel = document.getElementById('monitoringPanel');
        if (monitoringPanel) {
            monitoringPanel.classList.add('visible');
        }
    }

    hideMonitoringPanel() {
        const monitoringPanel = document.getElementById('monitoringPanel');
        if (monitoringPanel) {
            monitoringPanel.classList.remove('visible');
        }
    }

    renderEventLog() {
        const container = this.elements.eventLog;

        container.innerHTML = this.eventLogEntries.map(entry => `
            <div class="event-item ${entry.type}">
                [${entry.time}] ${entry.message}
            </div>
        `).join('');
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new RobotDashboard();
    dashboard.init();

    // Expose for debugging
    window.robotDashboard = dashboard;
});
