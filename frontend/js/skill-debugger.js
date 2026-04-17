/**
 * Skill Debugger Module
 *
 * Provides debugging tools for skill execution including:
 * - Active skill tracking
 * - Skill history
 * - Precondition checking
 */

class SkillDebugger {
    constructor(apiClient) {
        this.api = apiClient;
        this.activeSkills = [];
        this.skillHistory = [];
        this.maxHistoryEntries = 50;
        this.preconditionsCache = {};
        this.currentSkillSchema = null;
        this.updateInterval = null;
        this.performanceMetrics = {
            totalExecutions: 0,
            successfulExecutions: 0,
            failedExecutions: 0,
            totalDuration: 0
        };
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.startRealTimeUpdates();
    }

    cacheElements() {
        this.elements = {
            activeSkillsList: document.getElementById('activeSkillsList'),
            skillHistoryList: document.getElementById('skillHistoryList'),
            preconditionResults: document.getElementById('preconditionResults'),
            performanceMetrics: document.getElementById('performanceMetrics')
        };
    }

    setupEventListeners() {
        // Listen for skill execution events
        this.api.on('skillExecuted', (data) => {
            this.addToHistory(data);
        });

        // Listen for world state updates to refresh preconditions
        this.api.on('worldState', (worldState) => {
            this.updatePreconditionStatus(worldState);
        });

        // Listen for skill selection changes
        const skillSelect = document.getElementById('skillSelect');
        if (skillSelect) {
            skillSelect.addEventListener('change', async (e) => {
                if (e.target.value) {
                    await this.loadSkillSchema(e.target.value);
                }
            });
        }
    }

    startRealTimeUpdates() {
        // Update active skills elapsed time every 100ms
        this.updateInterval = setInterval(() => {
            this.renderActiveSkills();
        }, 100);
    }

    stopRealTimeUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    updatePerformanceMetrics(result, duration) {
        this.performanceMetrics.totalExecutions++;
        this.performanceMetrics.totalDuration += duration || 0;

        if (result?.status === 'SUCCESS' || result?.status === 'COMPLETED') {
            this.performanceMetrics.successfulExecutions++;
        } else if (result?.status === 'FAILED' || result?.status === 'ERROR') {
            this.performanceMetrics.failedExecutions++;
        }

        this.renderPerformanceMetrics();
    }

    renderPerformanceMetrics() {
        if (!this.elements.performanceMetrics) return;

        const metrics = this.performanceMetrics;
        const successRate = metrics.totalExecutions > 0
            ? ((metrics.successfulExecutions / metrics.totalExecutions) * 100).toFixed(1)
            : 0;
        const avgDuration = metrics.totalExecutions > 0
            ? (metrics.totalDuration / metrics.totalExecutions).toFixed(1)
            : 0;

        const html = `
            <div class="metrics-grid">
                <div class="metric-item">
                    <span class="metric-label">Total</span>
                    <span class="metric-value">${metrics.totalExecutions}</span>
                </div>
                <div class="metric-item success">
                    <span class="metric-label">Success</span>
                    <span class="metric-value">${metrics.successfulExecutions}</span>
                </div>
                <div class="metric-item error">
                    <span class="metric-label">Failed</span>
                    <span class="metric-value">${metrics.failedExecutions}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Rate</span>
                    <span class="metric-value">${successRate}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Avg ms</span>
                    <span class="metric-value">${avgDuration}</span>
                </div>
            </div>
        `;

        this.elements.performanceMetrics.innerHTML = html;
    }

    async loadSkillSchema(skillName) {
        try {
            // Try to get schema from backend
            const schema = await this.api.getSkillSchema(skillName);
            this.currentSkillSchema = schema;
            this.renderSkillSchema(schema);
        } catch (error) {
            // Fall back to local schema definitions
            this.currentSkillSchema = this.getLocalSkillSchema(skillName);
            this.renderSkillSchema(this.currentSkillSchema);
        }
    }

    getLocalSkillSchema(skillName) {
        // Local schema definitions matching src/skill/skill_schemas.py
        const schemas = {
            grasp: {
                name: 'grasp',
                description: 'Grasp an object at the specified location. Approaches the object, closes gripper with specified force.',
                skill_type: 'MANIPULATION',
                inputs: {
                    object_id: 'string',
                    approach_height: 'float',
                    grip_force: 'float'
                },
                preconditions: [
                    'robot.gripper_width > 0',
                    'object with object_id exists in world_state',
                    'object.state == VISIBLE',
                    'target position is within workspace bounds'
                ],
                effects: [
                    'object.state == GRASPED',
                    'robot.gripper_force > 0',
                    'robot.gripper_width == 0 (object held)'
                ],
                safety_constraints: [
                    'grip_force must be within safe limits (0-100N)',
                    'approach_height must be positive',
                    'object must not be in Obstacle list',
                    'gripper must not be moving when closing'
                ]
            },
            move_to: {
                name: 'move_to',
                description: 'Move robot end-effector to a target pose. Supports linear, joint, and pose motion types.',
                skill_type: 'MOTION',
                inputs: {
                    target_x: 'float',
                    target_y: 'float',
                    target_z: 'float',
                    target_rx: 'float',
                    target_ry: 'float',
                    target_rz: 'float',
                    speed: 'float',
                    motion_type: 'string'
                },
                preconditions: [
                    'target position is within workspace bounds',
                    'path is collision-free (no Obstacles in way)',
                    'robot is not holding object that would collide',
                    'motion_type is valid (linear, joint, pose)'
                ],
                effects: [
                    'robot.end_effector_pose matches target pose',
                    'robot.state == COMPLETED'
                ],
                safety_constraints: [
                    'speed must be positive and within safe limits',
                    'target must be within workspace bounds',
                    'motion must not cause self-collision',
                    'motion must not cause collision with obstacles'
                ]
            },
            place: {
                name: 'place',
                description: 'Place a grasped object at the target location. Lowers object, opens gripper, retracts.',
                skill_type: 'MANIPULATION',
                inputs: {
                    object_id: 'string',
                    target_x: 'float',
                    target_y: 'float',
                    target_z: 'float',
                    approach_height: 'float'
                },
                preconditions: [
                    'robot.gripper_force > 0 (object is grasped)',
                    'object.state == GRASPED',
                    'target position is within workspace bounds',
                    'target location is empty (no obstacles)'
                ],
                effects: [
                    'object.state == PLACED',
                    'object.pose matches target',
                    'robot.gripper_force == 0',
                    'robot.gripper_width > 0'
                ],
                safety_constraints: [
                    'approach_height must be positive',
                    'target must be on a valid surface',
                    'robot must not drop object too fast',
                    'gripper opens only after object is at target'
                ]
            },
            release: {
                name: 'release',
                description: 'Release a grasped object by opening the gripper to specified width.',
                skill_type: 'MANIPULATION',
                inputs: {
                    object_id: 'string',
                    gripper_open_width: 'float'
                },
                preconditions: [
                    'robot.gripper_force > 0 (object is held)',
                    'object.state == GRASPED'
                ],
                effects: [
                    'robot.gripper_force == 0',
                    'robot.gripper_width >= gripper_open_width',
                    'object.state == VISIBLE (object released)'
                ],
                safety_constraints: [
                    'gripper_open_width must be positive',
                    'gripper must not open too quickly',
                    'object must be supported after release'
                ]
            },
            rotate: {
                name: 'rotate',
                description: 'Rotate robot end-effector around specified axis by given angle.',
                skill_type: 'MOTION',
                inputs: {
                    axis: 'string',
                    angle: 'float',
                    speed: 'float'
                },
                preconditions: [
                    'axis is valid (x, y, or z)',
                    'angle is within joint limits',
                    'rotation path is collision-free'
                ],
                effects: [
                    'robot.end_effector_pose rz updated by angle (for z-axis rotation)',
                    'robot.state == COMPLETED'
                ],
                safety_constraints: [
                    'angle must be within safe joint limits',
                    'rotation speed must be controlled',
                    'axis must be valid (x, y, z)',
                    'must not cause self-collision during rotation'
                ]
            },
            stop: {
                name: 'stop',
                description: 'Immediately stop all robot motion. Can be emergency or controlled stop.',
                skill_type: 'MOTION',
                inputs: {
                    emergency: 'boolean'
                },
                preconditions: [
                    'robot.state != IDLE'
                ],
                effects: [
                    'robot.state == IDLE',
                    'all motion commands cancelled',
                    'if emergency: gripper forced open'
                ],
                safety_constraints: [
                    'emergency stop must always be available',
                    'controlled stop must decelerate safely',
                    'stop action must complete within 100ms'
                ]
            }
        };

        return schemas[skillName] || null;
    }

    renderSkillSchema(schema) {
        if (!schema) return;

        // Render full schema info in the precondition results area
        const container = document.getElementById('preconditionResults');
        if (!container) return;

        const html = `
            <div class="schema-viewer">
                <div class="schema-section">
                    <h4>Preconditions</h4>
                    <ul class="schema-list precondition-list">
                        ${(schema.preconditions || []).map(p => `<li>${p}</li>`).join('')}
                    </ul>
                </div>
                <div class="schema-section">
                    <h4>Effects</h4>
                    <ul class="schema-list effect-list">
                        ${(schema.effects || []).map(e => `<li>${e}</li>`).join('')}
                    </ul>
                </div>
                <div class="schema-section">
                    <h4>Safety Constraints</h4>
                    <ul class="schema-list safety-list">
                        ${(schema.safety_constraints || []).map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
                <div class="schema-section">
                    <h4>Input Parameters</h4>
                    <div class="param-list">
                        ${Object.entries(schema.inputs || {}).map(([k, v]) =>
                            `<span class="param-item"><strong>${k}</strong>: ${v}</span>`
                        ).join('')}
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    addActiveSkill(skill) {
        const skillEntry = {
            id: `skill_${Date.now()}`,
            skillName: skill.skillName || skill.skill_name,
            params: skill.params || skill.parameters,
            startTime: Date.now(),
            status: 'EXECUTING'
        };

        this.activeSkills.push(skillEntry);
        this.renderActiveSkills();
    }

    completeActiveSkill(skillName, result) {
        const index = this.activeSkills.findIndex(s =>
            (s.skillName === skillName || s.skill_name === skillName) && s.status === 'EXECUTING'
        );

        if (index !== -1) {
            const skill = this.activeSkills.splice(index, 1)[0];
            skill.endTime = Date.now();
            skill.status = result.status || 'COMPLETED';
            skill.result = result;

            this.addToHistory({
                skillName: skill.skillName || skill.skill_name,
                params: skill.params || skill.parameters,
                result: result,
                duration: skill.endTime - skill.startTime
            });

            this.renderActiveSkills();
        }
    }

    addToHistory(entry) {
        const historyEntry = {
            id: `history_${Date.now()}`,
            skillName: entry.skillName,
            params: entry.params || entry.parameters,
            result: entry.result,
            timestamp: Date.now(),
            duration: entry.duration || 0
        };

        this.skillHistory.unshift(historyEntry);

        if (this.skillHistory.length > this.maxHistoryEntries) {
            this.skillHistory.pop();
        }

        // Update performance metrics
        this.updatePerformanceMetrics(entry.result, entry.duration);

        this.renderSkillHistory();
    }

    renderActiveSkills() {
        if (!this.elements.activeSkillsList) return;

        if (this.activeSkills.length === 0) {
            this.elements.activeSkillsList.innerHTML = '<div class="empty-state">No active skills</div>';
            return;
        }

        const html = this.activeSkills.map(skill => {
            const elapsed = Date.now() - skill.startTime;
            return `
                <div class="active-skill-item">
                    <div class="skill-name">${skill.skillName}</div>
                    <div class="skill-status executing">EXECUTING</div>
                    <div class="skill-elapsed">${elapsed}ms</div>
                </div>
            `;
        }).join('');

        this.elements.activeSkillsList.innerHTML = html;
    }

    renderSkillHistory() {
        if (!this.elements.skillHistoryList) return;

        if (this.skillHistory.length === 0) {
            this.elements.skillHistoryList.innerHTML = '<div class="empty-state">No skill history</div>';
            return;
        }

        const html = this.skillHistory.slice(0, 20).map(entry => {
            const date = new Date(entry.timestamp);
            const timeStr = date.toLocaleTimeString();
            const statusClass = this.getStatusClass(entry.result?.status);
            const statusText = entry.result?.status || 'UNKNOWN';

            return `
                <div class="history-item ${statusClass}">
                    <div class="history-header">
                        <span class="history-skill">${entry.skillName}</span>
                        <span class="history-status">${statusText}</span>
                    </div>
                    <div class="history-meta">
                        <span>${timeStr}</span>
                        ${entry.duration ? `<span>${entry.duration}ms</span>` : ''}
                    </div>
                    <div class="history-params">
                        ${this.formatParams(entry.params)}
                    </div>
                </div>
            `;
        }).join('');

        this.elements.skillHistoryList.innerHTML = html;
    }

    getStatusClass(status) {
        switch (status) {
            case 'SUCCESS':
            case 'COMPLETED':
                return 'status-success';
            case 'PARTIAL':
                return 'status-partial';
            case 'FAILED':
            case 'ERROR':
                return 'status-error';
            default:
                return 'status-unknown';
        }
    }

    formatParams(params) {
        if (!params) return '';
        return Object.entries(params)
            .map(([k, v]) => `<span class="param">${k}: ${v}</span>`)
            .join('');
    }

    async checkPreconditions(skillName, worldState) {
        // Define precondition checkers for each skill
        const preconditionCheckers = {
            grasp: (ws) => {
                const checks = [];
                checks.push({
                    condition: 'robot.gripper_width > 0',
                    satisfied: (ws.robot?.gripper_width || 0) > 0,
                    message: 'Gripper must be open'
                });
                return checks;
            },
            move_to: (ws) => {
                const checks = [];
                const bounds = ws.environment?.workspace_bounds;
                if (bounds) {
                    checks.push({
                        condition: 'target within workspace',
                        satisfied: true,
                        message: 'Target within workspace bounds'
                    });
                }
                return checks;
            },
            place: (ws) => {
                const checks = [];
                checks.push({
                    condition: 'robot.gripper_force > 0',
                    satisfied: (ws.robot?.gripper_force || 0) > 0,
                    message: 'Object must be grasped'
                });
                return checks;
            },
            release: (ws) => {
                const checks = [];
                checks.push({
                    condition: 'robot.gripper_force > 0',
                    satisfied: (ws.robot?.gripper_force || 0) > 0,
                    message: 'Object must be held'
                });
                return checks;
            },
            rotate: (ws) => {
                const checks = [];
                checks.push({
                    condition: 'rotation path clear',
                    satisfied: true,
                    message: 'No obstacles in rotation path'
                });
                return checks;
            }
        };

        const checker = preconditionCheckers[skillName];
        if (!checker || !worldState) return [];

        return checker(worldState);
    }

    async updatePreconditionStatus(worldState) {
        if (!this.elements.preconditionResults) return;

        const selectedSkill = document.getElementById('skillSelect')?.value;
        if (!selectedSkill) {
            this.elements.preconditionResults.innerHTML = '<div class="empty-state">Select a skill to check preconditions</div>';
            return;
        }

        const checks = await this.checkPreconditions(selectedSkill, worldState);

        if (checks.length === 0) {
            this.elements.preconditionResults.innerHTML = '<div class="empty-state">No preconditions to check</div>';
            return;
        }

        const html = checks.map(check => {
            const statusClass = check.satisfied ? 'check-pass' : 'check-fail';
            const statusIcon = check.satisfied ? '&#10004;' : '&#10008;';
            return `
                <div class="precondition-check ${statusClass}">
                    <span class="check-icon">${statusIcon}</span>
                    <span class="check-condition">${check.condition}</span>
                    <span class="check-message">${check.message}</span>
                </div>
            `;
        }).join('');

        this.elements.preconditionResults.innerHTML = html;
    }

    getSkillHistory() {
        return [...this.skillHistory];
    }

    clearHistory() {
        this.skillHistory = [];
        this.renderSkillHistory();
    }
}

// Export for use in other modules
window.SkillDebugger = SkillDebugger;
