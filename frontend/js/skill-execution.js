/**
 * Skill Execution Module
 *
 * Handles skill selection, parameter input, execution, and result display.
 */

class SkillExecution {
    constructor(apiClient) {
        this.api = apiClient;
        this.selectedSkill = null;
        this.skillSchemas = {
            grasp: {
                name: 'grasp',
                description: 'Grasp an object at the specified location.',
                inputs: [
                    { name: 'object_id', type: 'text', label: 'Object ID', required: true },
                    { name: 'approach_height', type: 'number', label: 'Approach Height (m)', default: 0.1, min: 0.01 },
                    { name: 'grip_force', type: 'number', label: 'Grip Force (N)', default: 50, min: 0, max: 100 }
                ],
                preconditions: [
                    'robot.gripper_width > 0',
                    'object with object_id exists in world_state',
                    'object.state == VISIBLE',
                    'target position is within workspace bounds'
                ]
            },
            move_to: {
                name: 'move_to',
                description: 'Move robot end-effector to a target pose.',
                inputs: [
                    { name: 'target_x', type: 'number', label: 'Target X (m)', default: 0.0 },
                    { name: 'target_y', type: 'number', label: 'Target Y (m)', default: 0.0 },
                    { name: 'target_z', type: 'number', label: 'Target Z (m)', default: 0.0 },
                    { name: 'target_rx', type: 'number', label: 'Target RX (rad)', default: 0.0 },
                    { name: 'target_ry', type: 'number', label: 'Target RY (rad)', default: 0.0 },
                    { name: 'target_rz', type: 'number', label: 'Target RZ (rad)', default: 0.0 },
                    { name: 'speed', type: 'number', label: 'Speed', default: 1.0, min: 0.1, max: 1.0 },
                    { name: 'motion_type', type: 'select', label: 'Motion Type', options: ['linear', 'joint', 'pose'], default: 'linear' }
                ],
                preconditions: [
                    'target position is within workspace bounds',
                    'path is collision-free',
                    'motion_type is valid (linear, joint, pose)'
                ]
            },
            place: {
                name: 'place',
                description: 'Place a grasped object at the target location.',
                inputs: [
                    { name: 'object_id', type: 'text', label: 'Object ID', required: true },
                    { name: 'target_x', type: 'number', label: 'Target X (m)', default: 0.0 },
                    { name: 'target_y', type: 'number', label: 'Target Y (m)', default: 0.0 },
                    { name: 'target_z', type: 'number', label: 'Target Z (m)', default: 0.0 },
                    { name: 'approach_height', type: 'number', label: 'Approach Height (m)', default: 0.1, min: 0.01 }
                ],
                preconditions: [
                    'robot.gripper_force > 0 (object is grasped)',
                    'object.state == GRASPED',
                    'target position is within workspace bounds'
                ]
            },
            release: {
                name: 'release',
                description: 'Release a grasped object by opening the gripper.',
                inputs: [
                    { name: 'object_id', type: 'text', label: 'Object ID', required: true },
                    { name: 'gripper_open_width', type: 'number', label: 'Gripper Open Width (m)', default: 0.05, min: 0.0 }
                ],
                preconditions: [
                    'robot.gripper_force > 0 (object is held)',
                    'object.state == GRASPED'
                ]
            },
            rotate: {
                name: 'rotate',
                description: 'Rotate robot end-effector around specified axis.',
                inputs: [
                    { name: 'axis', type: 'select', label: 'Axis', options: ['x', 'y', 'z'], default: 'z' },
                    { name: 'angle', type: 'number', label: 'Angle (rad)', default: 1.57 },
                    { name: 'speed', type: 'number', label: 'Speed', default: 1.0, min: 0.1, max: 1.0 }
                ],
                preconditions: [
                    'axis is valid (x, y, or z)',
                    'angle is within joint limits',
                    'rotation path is collision-free'
                ]
            }
        };

        this.executing = false;
        this.debugPaused = false;
    }

    // Debug mode step-through support
    debugStep() {
        this.debugPaused = false;
        // Resume execution for one step
        console.log('Debug: Step executed');
    }

    debugContinue() {
        this.debugPaused = false;
        this.debugBreakpoints = [];
        console.log('Debug: Continued past breakpoints');
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
    }

    cacheElements() {
        this.elements = {
            skillSelect: document.getElementById('skillSelect'),
            skillParams: document.getElementById('skillParams'),
            skillDescription: document.getElementById('skillDescription'),
            skillPreconditions: document.getElementById('skillPreconditions'),
            executeSkillBtn: document.getElementById('executeSkillBtn'),
            skillResult: document.getElementById('skillResult')
        };
    }

    setupEventListeners() {
        if (this.elements.skillSelect) {
            this.elements.skillSelect.addEventListener('change', (e) => {
                this.onSkillSelect(e.target.value);
            });
        }

        if (this.elements.executeSkillBtn) {
            this.elements.executeSkillBtn.addEventListener('click', () => {
                this.executeSkill();
            });
        }
    }

    onSkillSelect(skillName) {
        this.selectedSkill = skillName;

        if (!skillName) {
            this.clearSkillUI();
            return;
        }

        const schema = this.skillSchemas[skillName];
        if (!schema) {
            console.error('Unknown skill:', skillName);
            return;
        }

        this.renderSkillUI(schema);
        this.elements.executeSkillBtn.disabled = false;
    }

    clearSkillUI() {
        this.elements.skillParams.innerHTML = '<p class="skill-hint">Select a skill to see its parameters</p>';
        this.elements.skillDescription.innerHTML = '';
        this.elements.skillPreconditions.innerHTML = '';
        this.elements.executeSkillBtn.disabled = true;
        this.elements.skillResult.innerHTML = '';
    }

    renderSkillUI(schema) {
        // Render description
        this.elements.skillDescription.innerHTML = `
            <div class="skill-desc-box">
                <p>${schema.description}</p>
            </div>
        `;

        // Render preconditions
        this.elements.skillPreconditions.innerHTML = `
            <div class="preconditions-box">
                <h4>Preconditions:</h4>
                <ul>
                    ${schema.preconditions.map(p => `<li>${p}</li>`).join('')}
                </ul>
            </div>
        `;

        // Render input parameters
        const paramsHtml = schema.inputs.map(input => {
            let inputHtml = '';

            if (input.type === 'select') {
                inputHtml = `
                    <select name="${input.name}" id="param_${input.name}" ${input.required ? 'required' : ''}>
                        ${input.options.map(opt => `
                            <option value="${opt}" ${opt === input.default ? 'selected' : ''}>${opt}</option>
                        `).join('')}
                    </select>
                `;
            } else {
                const attrs = [];
                if (input.min !== undefined) attrs.push(`min="${input.min}"`);
                if (input.max !== undefined) attrs.push(`max="${input.max}"`);
                if (input.step !== undefined) attrs.push(`step="${input.step}"`);
                if (input.default !== undefined) attrs.push(`value="${input.default}"`);

                inputHtml = `
                    <input type="${input.type}" name="${input.name}" id="param_${input.name}"
                           ${attrs.join(' ')} ${input.required ? 'required' : ''}>
                `;
            }

            return `
                <div class="param-item">
                    <label for="param_${input.name}">${input.label}:</label>
                    ${inputHtml}
                </div>
            `;
        }).join('');

        this.elements.skillParams.innerHTML = `
            <div class="skill-inputs">
                <h4>Parameters:</h4>
                ${paramsHtml}
            </div>
        `;
    }

    getSkillParams() {
        if (!this.selectedSkill) return null;

        const schema = this.skillSchemas[this.selectedSkill];
        if (!schema) return null;

        const params = {};

        schema.inputs.forEach(input => {
            const element = document.getElementById(`param_${input.name}`);
            if (element) {
                let value = element.value;
                if (input.type === 'number') {
                    value = parseFloat(value);
                }
                params[input.name] = value;
            }
        });

        return params;
    }

    async executeSkill() {
        if (!this.selectedSkill || this.executing) return;

        this.executing = true;
        this.elements.executeSkillBtn.disabled = true;
        this.elements.skillResult.innerHTML = '<div class="skill-executing">Executing...</div>';

        try {
            const params = this.getSkillParams();
            const result = await this.api.executeSkill(this.selectedSkill, params);

            if (result.status === 'SUCCESS' || result.status === 'COMPLETED') {
                this.elements.skillResult.innerHTML = `
                    <div class="skill-success">
                        <span class="skill-status">SUCCESS</span>
                        <p>${result.message || `Skill '${this.selectedSkill}' executed successfully`}</p>
                    </div>
                `;
            } else if (result.status === 'PARTIAL') {
                this.elements.skillResult.innerHTML = `
                    <div class="skill-partial">
                        <span class="skill-status">PARTIAL</span>
                        <p>${result.message || 'Skill partially completed'}</p>
                    </div>
                `;
            } else {
                this.elements.skillResult.innerHTML = `
                    <div class="skill-failed">
                        <span class="skill-status">FAILED</span>
                        <p>${result.message || 'Skill execution failed'}</p>
                    </div>
                `;
            }

            // Emit event for skill history
            this.api.emit('skillExecuted', {
                skillName: this.selectedSkill,
                params: params,
                result: result
            });

        } catch (error) {
            this.elements.skillResult.innerHTML = `
                <div class="skill-error">
                    <span class="skill-status">ERROR</span>
                    <p>${error.message}</p>
                </div>
            `;
        } finally {
            this.executing = false;
            this.elements.executeSkillBtn.disabled = false;
        }
    }
}

// Export for use in other modules
window.SkillExecution = SkillExecution;
