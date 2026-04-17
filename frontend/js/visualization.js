/**
 * Workspace Visualization Module
 *
 * Renders a 2D top-down view of the robot workspace including:
 * - Robot position and orientation
 * - Objects in the workspace
 * - Obstacles
 * - Workspace bounds
 */

class WorkspaceVisualization {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            throw new Error(`Canvas element '${canvasId}' not found`);
        }

        this.ctx = this.canvas.getContext('2d');

        // World bounds (from WorkspaceBounds in shared/world_state.py)
        this.worldBounds = {
            x_min: -0.5,
            x_max: 0.5,
            y_min: -0.5,
            y_max: 0.5,
            z_min: 0.0,
            z_max: 0.5
        };

        // Canvas scaling
        this.padding = 40;
        this.updateDimensions();

        // Colors
        this.colors = {
            background: '#0d1117',
            grid: '#1c2128',
            gridLine: '#30363d',
            workspace: '#161b22',
            workspaceBorder: '#4a90d9',
            robot: '#4a90d9',
            robotArm: '#3a7bc4',
            gripper: '#58a6ff',
            object: '#2ecc71',
            obstacle: '#e74c3c',
            text: '#a0a0a0'
        };

        // Animation
        this.animationFrame = null;
        this.robotPose = { x: 0, y: 0, z: 0, rz: 0 };
        this.targetPose = { x: 0, y: 0, z: 0, rz: 0 };
        this.objects = [];
        this.obstacles = [];
        this.animationSpeed = 0.1;

        // Gripper visualization
        this.gripperWidth = 0.0;

        // Start render loop
        this.startRenderLoop();
    }

    updateDimensions() {
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();

        // Set canvas size to match container
        this.canvas.width = Math.min(rect.width - 20, 500);
        this.canvas.height = Math.min(rect.height - 20, 400);

        // Calculate scale to fit world bounds in canvas
        const availableWidth = this.canvas.width - 2 * this.padding;
        const availableHeight = this.canvas.height - 2 * this.padding;

        const worldWidth = this.worldBounds.x_max - this.worldBounds.x_min;
        const worldHeight = this.worldBounds.y_max - this.worldBounds.y_min;

        this.scale = Math.min(availableWidth / worldWidth, availableHeight / worldHeight);

        // Calculate offset to center the workspace
        this.offsetX = (this.canvas.width - worldWidth * this.scale) / 2;
        this.offsetY = (this.canvas.height + worldHeight * this.scale) / 2; // +Y is down in canvas
    }

    // Convert world coordinates to canvas coordinates
    worldToCanvas(wx, wy) {
        return {
            x: this.offsetX + (wx - this.worldBounds.x_min) * this.scale,
            y: this.offsetY - (wy - this.worldBounds.y_min) * this.scale
        };
    }

    // Convert canvas coordinates to world coordinates
    canvasToWorld(cx, cy) {
        return {
            x: (cx - this.offsetX) / this.scale + this.worldBounds.x_min,
            y: (this.offsetY - cy) / this.scale + this.worldBounds.y_min
        };
    }

    updateWorldState(worldState) {
        if (worldState.robot && worldState.robot.end_effector_pose) {
            const ee = worldState.robot.end_effector_pose;
            this.targetPose = {
                x: ee.x,
                y: ee.y,
                z: ee.z,
                rz: ee.rz || 0
            };

            // Update gripper width
            this.gripperWidth = worldState.robot.gripper_width || 0;
        }

        // Update objects
        if (worldState.objects) {
            this.objects = worldState.objects.map(obj => ({
                id: obj.id,
                type: obj.type,
                x: obj.pose.x,
                y: obj.pose.y,
                z: obj.pose.z,
                color: obj.color || '#2ecc71',
                state: obj.state
            }));
        }

        // Update obstacles
        if (worldState.environment && worldState.environment.obstacles) {
            this.obstacles = worldState.environment.obstacles.map(obs => ({
                id: obs.id,
                x: obs.pose.x,
                y: obs.pose.y,
                z: obs.pose.z,
                shape: obs.shape,
                size: obs.size
            }));
        }

        // Update workspace bounds if provided
        if (worldState.environment && worldState.environment.workspace_bounds) {
            const bounds = worldState.environment.workspace_bounds;
            this.worldBounds = { ...bounds };
            this.updateDimensions();
        }
    }

    updateRobotPose(pose) {
        this.targetPose = pose;
    }

    updateGripper(width) {
        this.gripperWidth = width;
    }

    lerp(current, target, speed) {
        return current + (target - current) * speed;
    }

    startRenderLoop() {
        const render = () => {
            this.render();
            this.animationFrame = requestAnimationFrame(render);
        };
        render();
    }

    stopRenderLoop() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }

    render() {
        const ctx = this.ctx;
        const { width, height } = this.canvas;

        // Clear canvas
        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, width, height);

        // Draw workspace bounds
        this.drawWorkspace();

        // Draw grid
        this.drawGrid();

        // Draw obstacles
        this.drawObstacles();

        // Draw objects
        this.drawObjects();

        // Draw robot
        this.drawRobot();

        // Draw labels
        this.drawLabels();
    }

    drawWorkspace() {
        const ctx = this.ctx;
        const topLeft = this.worldToCanvas(this.worldBounds.x_min, this.worldBounds.y_max);
        const bottomRight = this.worldToCanvas(this.worldBounds.x_max, this.worldBounds.y_min);

        const w = bottomRight.x - topLeft.x;
        const h = topLeft.y - bottomRight.y;

        // Fill workspace area
        ctx.fillStyle = this.colors.workspace;
        ctx.fillRect(topLeft.x, bottomRight.y, w, h);

        // Draw border
        ctx.strokeStyle = this.colors.workspaceBorder;
        ctx.lineWidth = 2;
        ctx.strokeRect(topLeft.x, bottomRight.y, w, h);
    }

    drawGrid() {
        const ctx = this.ctx;
        const gridStep = 0.1; // 10cm grid

        ctx.strokeStyle = this.colors.gridLine;
        ctx.lineWidth = 0.5;

        // Vertical lines
        for (let x = this.worldBounds.x_min; x <= this.worldBounds.x_max; x += gridStep) {
            const p1 = this.worldToCanvas(x, this.worldBounds.y_min);
            const p2 = this.worldToCanvas(x, this.worldBounds.y_max);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
        }

        // Horizontal lines
        for (let y = this.worldBounds.y_min; y <= this.worldBounds.y_max; y += gridStep) {
            const p1 = this.worldToCanvas(this.worldBounds.x_min, y);
            const p2 = this.worldToCanvas(this.worldBounds.x_max, y);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
        }
    }

    drawObstacles() {
        const ctx = this.ctx;

        this.obstacles.forEach(obs => {
            const pos = this.worldToCanvas(obs.x, obs.y);
            const size = obs.size || { x: 0.05, y: 0.05 };

            ctx.fillStyle = this.colors.obstacle;
            ctx.globalAlpha = 0.7;

            if (obs.shape === 'sphere') {
                const radius = size.x * this.scale;
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
                ctx.fill();
            } else {
                // Default to box
                const w = size.x * this.scale;
                const h = size.y * this.scale;
                ctx.fillRect(pos.x - w/2, pos.y - h/2, w, h);
            }

            ctx.globalAlpha = 1.0;

            // Label
            ctx.fillStyle = this.colors.text;
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(obs.id, pos.x, pos.y - 15);
        });
    }

    drawObjects() {
        const ctx = this.ctx;

        this.objects.forEach(obj => {
            const pos = this.worldToCanvas(obj.x, obj.y);
            const size = 0.04; // Default object size

            ctx.fillStyle = obj.color || this.colors.object;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, size * this.scale, 0, Math.PI * 2);
            ctx.fill();

            // State indicator ring
            if (obj.state === 'grasped') {
                ctx.strokeStyle = '#f1c40f';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, size * this.scale + 5, 0, Math.PI * 2);
                ctx.stroke();
            } else if (obj.state === 'placed') {
                ctx.strokeStyle = '#2ecc71';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, size * this.scale + 5, 0, Math.PI * 2);
                ctx.stroke();
            }

            // Label
            ctx.fillStyle = this.colors.text;
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(obj.id, pos.x, pos.y + size * this.scale + 15);
        });
    }

    drawRobot() {
        const ctx = this.ctx;

        // Interpolate pose for smooth animation
        this.robotPose.x = this.lerp(this.robotPose.x, this.targetPose.x, this.animationSpeed);
        this.robotPose.y = this.lerp(this.robotPose.y, this.targetPose.y, this.animationSpeed);
        this.robotPose.z = this.lerp(this.robotPose.z, this.targetPose.z, this.animationSpeed);
        this.robotPose.rz = this.lerp(this.robotPose.rz, this.targetPose.rz, this.animationSpeed);

        const pos = this.worldToCanvas(this.robotPose.x, this.robotPose.y);

        // Draw robot base
        ctx.fillStyle = this.colors.robot;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 15, 0, Math.PI * 2);
        ctx.fill();

        // Draw robot arm direction
        const armLength = 20;
        const armAngle = -this.robotPose.rz; // Canvas Y is inverted
        const armEndX = pos.x + Math.cos(armAngle) * armLength;
        const armEndY = pos.y + Math.sin(armAngle) * armLength;

        ctx.strokeStyle = this.colors.robotArm;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
        ctx.lineTo(armEndX, armEndY);
        ctx.stroke();

        // Draw gripper
        const gripperLength = 15;
        const gripperSpread = this.gripperWidth * 10; // Scale gripper state

        // Left finger
        const leftAngle = armAngle - Math.PI/4;
        const leftEndX = armEndX + Math.cos(leftAngle) * gripperLength;
        const leftEndY = armEndY + Math.sin(leftAngle) * gripperLength;

        ctx.strokeStyle = this.colors.gripper;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(armEndX, armEndY);
        ctx.lineTo(leftEndX, leftEndY);
        ctx.stroke();

        // Right finger
        const rightAngle = armAngle + Math.PI/4;
        const rightEndX = armEndX + Math.cos(rightAngle) * gripperLength;
        const rightEndY = armEndY + Math.sin(rightAngle) * gripperLength;

        ctx.beginPath();
        ctx.moveTo(armEndX, armEndY);
        ctx.lineTo(rightEndX, rightEndY);
        ctx.stroke();

        // Draw Z-height indicator
        const heightRatio = (this.robotPose.z - this.worldBounds.z_min) /
                           (this.worldBounds.z_max - this.worldBounds.z_min);

        ctx.fillStyle = this.colors.text;
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(`Z: ${this.robotPose.z.toFixed(3)}m`, pos.x + 20, pos.y - 10);
    }

    drawLabels() {
        const ctx = this.ctx;
        const { width, height } = this.canvas;

        ctx.fillStyle = this.colors.text;
        ctx.font = '11px sans-serif';

        // X-axis label
        const xEnd = this.worldToCanvas(this.worldBounds.x_max, 0);
        ctx.textAlign = 'center';
        ctx.fillText('X', xEnd.x, height - 10);

        // Y-axis label
        const yEnd = this.worldToCanvas(0, this.worldBounds.y_max);
        ctx.textAlign = 'left';
        ctx.fillText('Y', 10, yEnd.y + 5);

        // Origin label
        const origin = this.worldToCanvas(0, 0);
        ctx.textAlign = 'right';
        ctx.fillText('0', origin.x - 5, origin.y + 15);

        // Title
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Top-Down View', width / 2, 20);
    }

    resize() {
        this.updateDimensions();
    }
}

// Export for use in other modules
window.WorkspaceVisualization = WorkspaceVisualization;
