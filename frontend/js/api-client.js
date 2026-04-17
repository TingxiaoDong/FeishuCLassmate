/**
 * API Client for Robot Control Dashboard
 *
 * Handles communication with the backend layers:
 * - World State updates (from shared world state)
 * - Robot status queries (via Robot API)
 * - Command execution (to Robot API)
 */

class RobotAPIClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.wsUrl = baseUrl.replace('http', 'ws');
        this.connected = false;
        this.wsRobot = null;
        this.wsWorldState = null;
        this.useMock = false;
        this._mockTime = 0;
        this.listeners = {
            worldState: [],
            robotStatus: [],
            connectionChange: [],
            error: [],
            skillExecuted: [],
            commandResult: []
        };
    }

    // ============================================================
    // Mock Mode Control
    // ============================================================

    setMockMode(enabled) {
        this.useMock = enabled;
        if (enabled) {
            this.connected = true;
            this.emit('connectionChange', { connected: true });
        }
    }

    isMockMode() {
        return this.useMock;
    }

    // ============================================================
    // Mock Data Generators
    // ============================================================

    _generateMockRobotStatus() {
        this._mockTime += 0.02;
        const t = this._mockTime;

        return {
            command_id: `mock_${Date.now()}`,
            state: Math.sin(t) > 0.9 ? 'EXECUTING' : 'IDLE',
            position: {
                x: 0.1 + Math.sin(t) * 0.1,
                y: Math.cos(t * 0.7) * 0.1,
                z: 0.2 + Math.sin(t * 1.3) * 0.05
            },
            joints: [0, 0, 0, 0, 0, 0],
            gripper_state: Math.max(0, Math.sin(t * 0.5) * 0.5),
            sensor_data: {},
            message: this.useMock ? 'Mock mode' : 'Ready'
        };
    }

    _generateMockWorldState() {
        this._mockTime += 0.01;
        const t = this._mockTime;

        return {
            timestamp: Date.now() / 1000,
            robot: {
                joint_positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                end_effector_pose: {
                    x: 0.1 + Math.sin(t) * 0.1,
                    y: Math.cos(t * 0.7) * 0.1,
                    z: 0.2 + Math.sin(t * 1.3) * 0.05
                },
                gripper_width: Math.max(0, Math.sin(t * 0.5) * 0.5),
                gripper_force: Math.max(0, Math.sin(t * 0.3) * 50)
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
    }

    _generateMockSkillResponse(skillName, params) {
        const skillStatuses = ['SUCCESS', 'FAILED', 'PARTIAL'];
        const status = skillStatuses[Math.floor(Math.random() * skillStatuses.length)];

        return {
            task_id: `skill_${Date.now()}`,
            skill_name: skillName,
            status: status,
            result: {
                executed_params: params,
                execution_time: Math.random() * 1000
            },
            message: status === 'SUCCESS'
                ? `Skill '${skillName}' executed successfully`
                : status === 'PARTIAL'
                    ? `Skill '${skillName}' partially completed`
                    : `Skill '${skillName}' failed`
        };
    }

    // ============================================================
    // Connection Management
    // ============================================================

    connect() {
        return new Promise((resolve, reject) => {
            try {
                // Connect to robot status WebSocket
                this.wsRobot = new WebSocket(`${this.wsUrl}/ws/robot`);

                this.wsRobot.onopen = () => {
                    this.connected = true;
                    this.emit('connectionChange', { connected: true });
                    resolve();
                };

                this.wsRobot.onclose = () => {
                    this.connected = false;
                    this.emit('connectionChange', { connected: false });
                };

                this.wsRobot.onerror = (error) => {
                    this.emit('error', { message: 'WebSocket connection error' });
                    reject(error);
                };

                this.wsRobot.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleRobotMessage(data);
                    } catch (e) {
                        console.error('Failed to parse robot message:', e);
                    }
                };

                // Connect to world state WebSocket
                this.wsWorldState = new WebSocket(`${this.wsUrl}/ws/world-state`);

                this.wsWorldState.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleWorldStateMessage(data);
                    } catch (e) {
                        console.error('Failed to parse world state message:', e);
                    }
                };

            } catch (error) {
                reject(error);
            }
        });
    }

    disconnect() {
        if (this.wsRobot) {
            this.wsRobot.close();
            this.wsRobot = null;
        }
        if (this.wsWorldState) {
            this.wsWorldState.close();
            this.wsWorldState = null;
        }
        this.connected = false;
    }

    handleRobotMessage(data) {
        // Handle robot status message
        if (data.state || data.position) {
            this.emit('robotStatus', data);
        } else {
            this.emit('robotStatus', data);
        }
    }

    handleWorldStateMessage(data) {
        // Handle world state message
        if (data.robot || data.objects) {
            this.emit('worldState', data);
        } else {
            this.emit('worldState', data);
        }
    }

    handleMessage(data) {
            case 'world_state':
                this.emit('worldState', data.payload);
                break;
            case 'robot_status':
                this.emit('robotStatus', data.payload);
                break;
            case 'command_result':
                this.handleCommandResult(data.payload);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    // ============================================================
    // Event System
    // ============================================================

    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
    }

    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
    }

    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => callback(data));
        }
    }

    // ============================================================
    // World State API (Shared Layer)
    // ============================================================

    async getWorldState() {
        if (this.useMock) {
            return this._generateMockWorldState();
        }
        const response = await fetch(`${this.baseUrl}/api/world-state`);
        if (!response.ok) {
            throw new Error(`Failed to get world state: ${response.statusText}`);
        }
        return response.json();
    }

    subscribeToWorldState(callback) {
        this.on('worldState', callback);
        return () => this.off('worldState', callback);
    }

    // ============================================================
    // Robot Status API (Robot Control API Layer)
    // ============================================================

    async getRobotStatus() {
        if (this.useMock) {
            return this._generateMockRobotStatus();
        }
        const response = await fetch(`${this.baseUrl}/api/robot/status`);
        if (!response.ok) {
            throw new Error(`Failed to get robot status: ${response.statusText}`);
        }
        return response.json();
    }

    async getRobotState() {
        const response = await fetch(`${this.baseUrl}/api/robot/state`);
        if (!response.ok) {
            throw new Error(`Failed to get robot state: ${response.statusText}`);
        }
        return response.json();
    }

    async getJointPositions() {
        const response = await fetch(`${this.baseUrl}/api/robot/joints`);
        if (!response.ok) {
            throw new Error(`Failed to get joint positions: ${response.statusText}`);
        }
        return response.json();
    }

    subscribeToRobotStatus(callback) {
        this.on('robotStatus', callback);
        return () => this.off('robotStatus', callback);
    }

    // ============================================================
    // Command API (To Robot Control API Layer)
    // ============================================================

    async sendCommand(action, params = {}) {
        const command = {
            command_id: `${action}_${Date.now()}`,
            action: action,
            params: params
        };

        const response = await fetch(`${this.baseUrl}/api/robot/command`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(command)
        });

        if (!response.ok) {
            throw new Error(`Failed to send command: ${response.statusText}`);
        }
        return response.json();
    }

    // Movement commands
    async moveTo(x, y, z, speed = 1.0) {
        return this.sendCommand('MOVE', { x, y, z, speed });
    }

    async moveRelative(dx, dy, dz, speed = 1.0) {
        return this.sendCommand('MOVE', {
            x: dx, y: dy, z: dz, speed
        });
    }

    // Gripper commands
    async grip(force = 0.5, position = 0.0) {
        return this.sendCommand('GRIP', { force, position });
    }

    async release() {
        return this.sendCommand('GRIP', { force: 0.0, position: 1.0 });
    }

    // Action commands
    async lift(height, speed = 1.0) {
        return this.sendCommand('LIFT', { height, speed });
    }

    async place(x, y, z) {
        return this.sendCommand('PLACE', { x, y, z });
    }

    async rotate(angle, axis = 'z') {
        return this.sendCommand('ROTATE', { angle, axis });
    }

    // System commands
    async stop() {
        return this.sendCommand('STOP', {});
    }

    async emergencyStop() {
        return this.sendCommand('STOP', { emergency: true });
    }

    async reset() {
        const response = await fetch(`${this.baseUrl}/api/robot/reset`, {
            method: 'POST'
        });
        if (!response.ok) {
            throw new Error(`Failed to reset robot: ${response.statusText}`);
        }
        return response.json();
    }

    // ============================================================
    // Task/Mission API (Planner Layer)
    // ============================================================

    async executeTask(instruction, context = {}) {
        const response = await fetch(`${this.baseUrl}/api/planner/task`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                instruction,
                context
            })
        });
        if (!response.ok) {
            throw new Error(`Failed to execute task: ${response.statusText}`);
        }
        return response.json();
    }

    async getTaskStatus(taskId) {
        const response = await fetch(`${this.baseUrl}/api/planner/task/${taskId}`);
        if (!response.ok) {
            throw new Error(`Failed to get task status: ${response.statusText}`);
        }
        return response.json();
    }

    // ============================================================
    // Skill API (Skill Layer)
    // ============================================================

    async executeSkill(skillName, parameters = {}) {
        if (this.useMock) {
            const result = this._generateMockSkillResponse(skillName, parameters);
            this.emit('skillExecuted', { skillName, parameters, result });
            return result;
        }
        const response = await fetch(`${this.baseUrl}/api/skills/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                skill_name: skillName,
                parameters: parameters
            })
        });
        if (!response.ok) {
            throw new Error(`Failed to execute skill: ${response.statusText}`);
        }
        return response.json();
    }

    async getSkillSchema(skillName) {
        if (this.useMock) {
            // Return local schema in mock mode
            const schemas = {
                grasp: { name: 'grasp', skill_type: 'MANIPULATION', inputs: { object_id: 'string', approach_height: 'float', grip_force: 'float' } },
                move_to: { name: 'move_to', skill_type: 'MOTION', inputs: { target_x: 'float', target_y: 'float', target_z: 'float', speed: 'float', motion_type: 'string' } },
                place: { name: 'place', skill_type: 'MANIPULATION', inputs: { object_id: 'string', target_x: 'float', target_y: 'float', target_z: 'float', approach_height: 'float' } },
                release: { name: 'release', skill_type: 'MANIPULATION', inputs: { object_id: 'string', gripper_open_width: 'float' } },
                rotate: { name: 'rotate', skill_type: 'MOTION', inputs: { axis: 'string', angle: 'float', speed: 'float' } },
                stop: { name: 'stop', skill_type: 'MOTION', inputs: { emergency: 'boolean' } }
            };
            return schemas[skillName] || { error: 'Skill not found' };
        }
        const response = await fetch(`${this.baseUrl}/api/skills/${skillName}/schema`);
        if (!response.ok) {
            throw new Error(`Failed to get skill schema: ${response.statusText}`);
        }
        return response.json();
    }

    async listSkills() {
        if (this.useMock) {
            return ['grasp', 'move_to', 'place', 'release', 'rotate', 'stop'];
        }
        const response = await fetch(`${this.baseUrl}/api/skills/list`);
        if (!response.ok) {
            throw new Error(`Failed to list skills: ${response.statusText}`);
        }
        return response.json();
    }

    subscribeToSkillExecution(callback) {
        this.on('skillExecuted', callback);
        return () => this.off('skillExecuted', callback);
    }

    // ============================================================
    // Result Handling
    // ============================================================

    handleCommandResult(payload) {
        console.log('Command result:', payload);
        this.emit('commandResult', payload);
    }
}

// Export for use in other modules
window.RobotAPIClient = RobotAPIClient;
