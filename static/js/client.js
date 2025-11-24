// Beach Rally Game Client
class GameClient {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Preload SVG assets (background, car, palm)
		this.assets = {
            background: null,
            car: null,
			palm: null,
			wave: null
        };
        this._loadAssets();

        // Initialize Socket.IO with correct configuration
        this.socket = io({
            transports: ['websocket', 'polling'],
            cors: {
                origin: "*",
                methods: ["GET", "POST"]
            }
        });
        
        // Game state
        this.gameState = null;
        
        // Connection event handlers
        this.socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
        });
        
        this.socket.on('error', (error) => {
            console.error('Socket error:', error);
        });
        
        // Resize canvas
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
        
        // Sound effects
        this.sounds = {
            engine: new Audio('/static/assets/engine.mp3'),
            collision: new Audio('/static/assets/collision.mp3'),
            pickup: new Audio('/static/assets/pickup.mp3'),
            checkpoint: new Audio('/static/assets/checkpoint.mp3')
        };
        
        // Set up input handling
        this.setupInput();
        
        // Set up socket events
        this.socket.on('game_state', (state) => this.handleServerUpdate(state));
        
        // Start game loop
        requestAnimationFrame(() => this.gameLoop());
    }

	_loadAssets() {
		const createImgFromSvg = (svgText) => {
			const img = new Image();
			img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgText);
			return img;
		};

		// Car SVG (kite-styled per user request)
		const CAR_SVG = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 640" width="420" height="640" role="img" aria-labelledby="titleDesc">
  <title id="titleDesc">Paper diamond kite with tail</title>
  <desc>Stylized paper kite with cross spars, pattern, and a tail of bows.</desc>
  <defs>
    <linearGradient id="kiteGrad" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#ffd166"/>
      <stop offset="1" stop-color="#ef476f"/>
    </linearGradient>
    <linearGradient id="paperShine" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="rgba(255,255,255,0.45)"/>
      <stop offset="1" stop-color="rgba(255,255,255,0)"/>
    </linearGradient>
    <filter id="softShadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity="0.2"/>
    </filter>
    <pattern id="diagStripes" patternUnits="userSpaceOnUse" width="12" height="12" patternTransform="rotate(25)">
      <rect width="6" height="12" fill="rgba(255,255,255,0.14)"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="#d7f0ff"/>
  <g transform="translate(210,200)" filter="url(#softShadow)">
    <g id="kite">
      <polygon points="0,-120 95,0 0,120 -95,0" fill="url(#kiteGrad)" stroke="#b33a4a" stroke-width="4" stroke-linejoin="round"/>
      <polygon points="0,-120 95,0 0,40 -55,-55" fill="url(#paperShine)" opacity="0.7" />
      <polygon points="0,-120 95,0 0,120 -95,0" fill="url(#diagStripes)" opacity="0.25"/>
      <polygon points="0,-120 0,0 -95,0" fill="#ffd166" opacity="0.25"/>
      <polygon points="0,120 0,0 95,0" fill="#ffffff" opacity="0.08"/>
    </g>
    <g stroke="#6b4226" stroke-linecap="round" stroke-linejoin="round">
      <line x1="0" y1="-132" x2="0" y2="132" stroke-width="6" />
      <line x1="-106" y1="0" x2="106" y2="0" stroke-width="6" />
      <circle cx="0" cy="0" r="6" fill="#6b4226" />
    </g>
    <g fill="#5a2f1a" opacity="0.9">
      <circle cx="0" cy="-120" r="3"/>
      <circle cx="95" cy="0" r="3"/>
      <circle cx="0" cy="120" r="3"/>
      <circle cx="-95" cy="0" r="3"/>
    </g>
  </g>
  <g transform="translate(210,320)">
    <path d="M0,120 C 10,150 30,200 2,240 C -28,286 -8,340 18,372 C 46,406 30,460 -14,480" fill="none" stroke="#7a7a7a" stroke-width="2" stroke-linecap="round" />
    <g id="bows" fill="#ff9aa2" stroke="#c75b6b" stroke-width="1.5">
      <path d="M2,240 m-10,-6 c -6,-4 -6,8 0,4 l10,4 l-10,4 c -6,4 -6,-8 0,-4 z" transform="translate(-6,0)"/>
      <path d="M2,240 m20,30 c -6,-4 -6,8 0,4 l10,4 l-10,4 c -6,4 -6,-8 0,-4 z" transform="translate(-6,24)"/>
      <path d="M2,240 m-16,78 c -6,-4 -6,8 0,4 l10,4 l-10,4 c -6,4 -6,-8 0,-4 z" transform="translate(-6,72)"/>
      <path d="M2,240 m10,118 c -6,-4 -6,8 0,4 l10,4 l-10,4 c -6,4 -6,-8 0,-4 z" transform="translate(-6,110)"/>
    </g>
  </g>
  <g transform="translate(210,320)">
    <circle cx="-14" cy="480" r="4" fill="#333" />
    <path d="M-14,484 L-14,620" stroke="#333" stroke-width="2" stroke-linecap="round" />
  </g>
</svg>`;

		// Background SVG
		const BG_SVG = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" width="900" height="600" role="img" aria-labelledby="titleDesc">
  <title id="titleDesc">Tropical palm tree scene</title>
  <desc>Two stylized palm trees on a small sandy island with waves and a warm sun.</desc>
  <defs>
    <linearGradient id="skyGrad" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#87CEEB"/>
      <stop offset="1" stop-color="#b8ebff"/>
    </linearGradient>
    <radialGradient id="sunGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="#fff59a"/>
      <stop offset="1" stop-color="#ffd166"/>
    </radialGradient>
    <linearGradient id="sandGrad" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#ffe9b3"/>
      <stop offset="1" stop-color="#ffd18a"/>
    </linearGradient>
    <linearGradient id="leafGrad" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#38b000"/>
      <stop offset="1" stop-color="#1b7a2f"/>
    </linearGradient>
    <filter id="softShadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="8" stdDeviation="18" flood-color="#000" flood-opacity="0.12"/>
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="url(#skyGrad)"/>
  <g transform="translate(150,110)">
    <circle cx="0" cy="0" r="64" fill="url(#sunGrad)" />
    <circle cx="0" cy="0" r="110" fill="#fff3bf" opacity="0.08"/>
  </g>
  <g transform="translate(0,360)">
    <path d="M0,80 C120,20 240,140 360,80 C480,20 600,140 720,80 C840,20 900,140 1200,80 L1200,200 L0,200 Z" fill="#9be7ff" opacity="0.7"/>
    <path d="M0,100 C120,40 240,160 360,100 C480,40 600,160 720,100 C840,40 900,160 1200,100 L1200,200 L0,200 Z" fill="#7fd4ff" opacity="0.5"/>
  </g>
  <g transform="translate(450,420)" filter="url(#softShadow)">
    <ellipse cx="0" cy="70" rx="260" ry="70" fill="url(#sandGrad)" />
    <ellipse cx="0" cy="40" rx="220" ry="45" fill="#fff1d0" opacity="0.18"/>
  </g>
  <g transform="translate(450,360)">
    <g id="palm-right" transform="translate(120,-40) rotate(-6)">
      <path d="M0,0 C6,-40 14,-100 18,-160 C20,-190 12,-220 8,-260 C6,-290 -2,-310 -10,-330" fill="none" stroke="#8b5a2b" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M-3,-40 C0,-20 8,0 12,20" stroke="#7a4f20" stroke-width="4" stroke-linecap="round" opacity="0.7" fill="none"/>
      <g transform="translate(-14,-330)">
        <path d="M0,0 C-120,20 -140,80  -40,120 C-100,80 -20,20 0,0 Z" fill="url(#leafGrad)"/>
        <path d="M0,0 C40,30 100,50 140,20 C100,60 40,40 0,0 Z" fill="url(#leafGrad)" opacity="0.95"/>
        <path d="M0,0 C-90,-30 -160,-10 -180,50 C-120,20 -60,10 0,0 Z" fill="url(#leafGrad)" opacity="0.95"/>
      </g>
      <g transform="translate(-10,-260)">
        <circle cx="0" cy="0" r="10" fill="#6b3e12"/>
        <circle cx="18" cy="6" r="10" fill="#6b3e12"/>
        <circle cx="-14" cy="8" r="9" fill="#5b3410"/>
      </g>
    </g>
    <g id="palm-left" transform="translate(-120,-20) rotate(14)">
      <path d="M0,0 C8,-30 22,-70 30,-110 C36,-140 32,-170 28,-195 C24,-220 12,-245 2,-265" fill="none" stroke="#8b5a2b" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
      <g transform="translate(-8,-265)">
        <path d="M0,0 C-110,10 -130,70 -40,100 C-100,70 -30,20 0,0 Z" fill="url(#leafGrad)"/>
        <path d="M0,0 C60,24 120,36 150,6 C110,38 60,30 0,0 Z" fill="url(#leafGrad)" opacity="0.95"/>
        <path d="M0,0 C-72,-18 -140,-4 -160,34 C-120,10 -60,6 0,0 Z" fill="url(#leafGrad)" opacity="0.95"/>
      </g>
      <g transform="translate(-6,-210)">
        <circle cx="0" cy="0" r="9" fill="#6b3e12"/>
        <circle cx="18" cy="6" r="8" fill="#5b3410"/>
      </g>
    </g>
  </g>
  <g transform="translate(450,500)">
    <path d="M-120,10 c30,-8 70,-12 120,-12 c50,0 90,4 120,12" fill="none" stroke="#ffd8a8" stroke-width="6" stroke-linecap="round" opacity="0.9"/>
    <path d="M-220,-20 q8,-20 20,0" stroke="#2c8c3a" stroke-width="3" stroke-linecap="round" fill="none"/>
    <path d="M260,-18 q-6,-18 -18,0" stroke="#2c8c3a" stroke-width="3" stroke-linecap="round" fill="none"/>
  </g>
  <g transform="translate(0,420)">
    <path d="M0,40 C80,0 160,80 240,40 C320,0 400,80 480,40 C560,0 640,80 720,40 C800,0 900,80 980,40" fill="none" stroke="#e6fbff" stroke-width="6" stroke-linecap="round" opacity="0.85"/>
  </g>
</svg>`;

		// Palm SVG (animated flow aesthetic)
		const PALM_SVG = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 420" width="900" height="420">
  <defs>
    <linearGradient id="flowGrad" x1="0" x2="1">
      <stop offset="0%" stop-color="#bfe9ff"/>
      <stop offset="100%" stop-color="#8ec9ff"/>
    </linearGradient>
    <radialGradient id="vortexGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#a9d6ff" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#a9d6ff" stop-opacity="0.0"/>
    </radialGradient>
    <style>
      .flow { fill: none; stroke: url(#flowGrad); stroke-width: 8; stroke-linecap: round; stroke-dasharray: 40 20; opacity: 0.25; }
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#f6fbff"/>
  <g>
    <path class="flow" d="M40,70 C160,70 320,70 520,70 C620,70 680,76 740,100" />
    <path class="flow" d="M30,110 C150,120 300,140 520,150 C620,156 690,160 740,170" />
    <path class="flow" d="M20,150 C140,170 300,190 520,200 C610,208 680,210 740,220" />
  </g>
  <g>
    <circle cx="720" cy="210" r="72" fill="url(#vortexGlow)" />
  </g>
</svg>`;

		// Wave SVG (spiral animation)
		const WAVE_SVG = `<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="500" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg">
  <path d="M250,250 m-200,0 c50,-40 150,-40 200,0 c50,40 150,40 200,0" stroke="black" stroke-width="50" fill="none" stroke-opacity="0.15">
    <animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 250 250" to="360 250 250" dur="40s" repeatCount="indefinite"/>
  </path>
  <path d="M250,250 m-120,0 c40,-30 100,-30 120,0 c20,30 100,30 120,0" stroke="black" stroke-width="40" fill="none" stroke-opacity="0.25">
    <animateTransform attributeName="transform" attributeType="XML" type="rotate" from="360 250 250" to="0 250 250" dur="25s" repeatCount="indefinite"/>
  </path>
  <path d="M250,250 m-60,0 c20,-20 60,-20 80,0 c20,20 60,20 80,0" stroke="black" stroke-width="30" fill="none" stroke-opacity="0.35">
    <animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 250 250" to="360 250 250" dur="16s" repeatCount="indefinite"/>
  </path>
</svg>`;

		this.assets.car = createImgFromSvg(CAR_SVG);
		this.assets.background = createImgFromSvg(BG_SVG);
		this.assets.palm = createImgFromSvg(PALM_SVG);
		this.assets.wave = createImgFromSvg(WAVE_SVG);
	}

	_drawBackground() {
		// Fit background to canvas size
		const img = this.assets.background;
		if (!img) return;
		this.ctx.save();
		this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
		this.ctx.restore();
	}
    
    resizeCanvas() {
        this.canvas.width = this.canvas.clientWidth;
        this.canvas.height = this.canvas.clientHeight;
    }
    
    setupInput() {
        document.addEventListener('keydown', (event) => {
            // Check for restart hotkey
            if (event.key.toLowerCase() === 'r' && event.ctrlKey) {
                event.preventDefault();
                startNewGame();
                return;
            }
            
            this.socket.emit('input', {
                type: 'keydown',
                key: event.key
            });
        });
        
        document.addEventListener('keyup', (event) => {
            this.socket.emit('input', {
                type: 'keyup',
                key: event.key
            });
        });
    }
    
    gameLoop() {
        this.render();
        requestAnimationFrame(() => this.gameLoop());
    }
    
    render() {
        if (!this.gameState) {
            // Draw loading screen
            this.ctx.fillStyle = '#000';
            this.ctx.font = '24px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('Connecting to game...', this.canvas.width/2, this.canvas.height/2);
            return;
        }
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw SVG background if loaded
        if (this.assets.background && this.assets.background.complete) {
            this._drawBackground();
        }
        
        // Draw background grid for reference
        this.drawGrid();
        
        // Draw entities
        if (this.gameState.entities) {
            for (const entity of this.gameState.entities) {
                // Use screen coordinates if available, otherwise use world coordinates
                const entityCopy = {...entity};
                entityCopy.x = entity.screen_x !== undefined ? entity.screen_x : entity.x;
                entityCopy.y = entity.screen_y !== undefined ? entity.screen_y : entity.y;
                this.drawEntity(entityCopy);
            }
        }
        
        // Draw collectibles
        if (this.gameState.collectibles) {
            for (const collectible of this.gameState.collectibles) {
                if (!collectible.collected) {
                    // Use screen coordinates if available, otherwise use world coordinates
                    const collectibleCopy = {...collectible};
                    collectibleCopy.x = collectible.screen_x !== undefined ? collectible.screen_x : collectible.x;
                    collectibleCopy.y = collectible.screen_y !== undefined ? collectible.screen_y : collectible.y;
                    this.drawCollectible(collectibleCopy);
                }
            }
        }
        
        // Draw player
        if (this.gameState.player) {
            const player = this.gameState.player;
            this.ctx.save();
            // Use screen coordinates if available, otherwise use world coordinates
            const playerX = player.screen_x !== undefined ? player.screen_x : player.x;
            const playerY = player.screen_y !== undefined ? player.screen_y : player.y;
            this.ctx.translate(playerX, playerY);
            this.ctx.rotate(player.rotation * Math.PI / 180);

            // Prefer SVG car sprite if available; fallback to rectangle
            if (this.assets.car && this.assets.car.complete) {
                const img = this.assets.car;
                // Original SVG nominal size 420x640; scale to player width/height
                const targetW = Math.max(1, player.width);
                const targetH = Math.max(1, player.height);
                this.ctx.drawImage(img, -targetW/2, -targetH/2, targetW, targetH);
            } else {
                // Fallback simple shape
                this.ctx.fillStyle = '#ff4444';
                this.ctx.fillRect(-player.width/2, -player.height/2, player.width, player.height);
            }

            this.ctx.restore();
        }
        
        // Update UI with improved formatting
        const scoreElement = document.getElementById('score-value');
        const timeElement = document.getElementById('time-value');
        const levelElement = document.getElementById('level-value');
        
        if (scoreElement) scoreElement.textContent = this.gameState.score || 0;
        if (timeElement) timeElement.textContent = 
            Math.ceil(this.gameState.timeLeft || 0).toString().padStart(2, '0');
        if (levelElement) levelElement.textContent = this.gameState.level || 1;
        
        // Draw powerup indicator
        if (this.gameState.active_powerup) {
            this.drawPowerupIndicator(this.gameState.active_powerup);
        }
        
        // Draw game bounds
        this.ctx.strokeStyle = '#ff0000';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    drawGrid() {
        // Draw a light grid for better spatial reference
        this.ctx.strokeStyle = '#e0e0e0';
        this.ctx.lineWidth = 1;
        
        // Vertical lines
        for (let x = 0; x < this.canvas.width; x += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        
        // Horizontal lines
        for (let y = 0; y < this.canvas.height; y += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    getEntityColor(type) {
        switch(type) {
            case 'rock': return '#666666';
            case 'palmtree': return '#2d5a27';
            case 'wave': return '#4444ff';
            default: return '#000000';
        }
    }
    
    drawEntity(entity) {
        this.ctx.save();
        this.ctx.translate(entity.x, entity.y);
        
        switch(entity.type) {
            case 'rock':
                // Draw a detailed rock
                this.ctx.fillStyle = '#666666';
                this.ctx.beginPath();
                this.ctx.arc(0, 0, entity.width/2, 0, Math.PI * 2);
                this.ctx.fill();
                // Add some texture
                this.ctx.strokeStyle = '#555555';
                this.ctx.lineWidth = 2;
                this.ctx.beginPath();
                this.ctx.arc(-5, -5, 5, 0, Math.PI * 2);
                this.ctx.stroke();
                break;
                
            case 'palmtree':
                if (this.assets.palm && this.assets.palm.complete) {
                    const img = this.assets.palm;
                    const w = Math.max(1, entity.width);
                    const h = Math.max(1, entity.height);
                    this.ctx.drawImage(img, -w/2, -h/2, w, h);
                } else {
                    // Fallback stylized palm
                    this.ctx.fillStyle = '#8B4513';
                    this.ctx.fillRect(-5, -entity.height/2, 10, entity.height);
                    this.ctx.fillStyle = '#2d5a27';
                    for (let angle = 0; angle < Math.PI * 2; angle += Math.PI/4) {
                        this.ctx.save();
                        this.ctx.rotate(angle);
                        this.ctx.beginPath();
                        this.ctx.ellipse(0, -entity.height/2, 20, 8, 0, 0, Math.PI * 2);
                        this.ctx.fill();
                        this.ctx.restore();
                    }
                }
                break;
                
            case 'wave':
                if (this.assets.wave && this.assets.wave.complete) {
                    const img = this.assets.wave;
                    // Make waves larger and impactful
                    const w = Math.max(1, entity.width * 1.6);
                    const h = Math.max(1, entity.height * 1.6);
                    this.ctx.drawImage(img, -w/2, -h/2, w, h);
                } else {
                    // Fallback: sine animated shape until SVG loads
                    this.ctx.fillStyle = 'rgba(68, 68, 255, 0.5)';
                    this.ctx.beginPath();
                    const time = Date.now() / 1000;
                    for (let x = -entity.width/2; x < entity.width/2; x++) {
                        const y = Math.sin(x/10 + time) * 5;
                        if (x === -entity.width/2) {
                            this.ctx.moveTo(x, y);
                        } else {
                            this.ctx.lineTo(x, y);
                        }
                    }
                    this.ctx.lineTo(entity.width/2, entity.height);
                    this.ctx.lineTo(-entity.width/2, entity.height);
                    this.ctx.closePath();
                    this.ctx.fill();
                }
                break;
        }
        
        this.ctx.restore();
    }
    
    drawCollectible(collectible) {
        this.ctx.save();
        this.ctx.translate(collectible.x, collectible.y);
        
        switch(collectible.type) {
            case 'coin':
                // Draw coin with animation
                const scale = 1 + Math.sin(Date.now() / 200) * 0.1;
                this.ctx.scale(scale, scale);
                
                // Outer circle
                this.ctx.fillStyle = '#ffd700';
                this.ctx.beginPath();
                this.ctx.arc(0, 0, 15, 0, Math.PI * 2);
                this.ctx.fill();
                
                // Inner circle
                this.ctx.fillStyle = '#ffc600';
                this.ctx.beginPath();
                this.ctx.arc(0, 0, 12, 0, Math.PI * 2);
                this.ctx.fill();
                
                // "$" symbol
                this.ctx.fillStyle = '#fff';
                this.ctx.font = 'bold 16px Arial';
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText('$', 0, 0);
                break;
                
            case 'powerup':
                // Draw powerup with pulsing effect
                const time = Date.now() / 1000;
                const alpha = 0.5 + Math.sin(time * 4) * 0.3;
                
                this.ctx.fillStyle = `rgba(255, 0, 255, ${alpha})`;
                this.ctx.beginPath();
                this.ctx.moveTo(0, -15);
                
                // Draw star shape
                for (let i = 0; i < 5; i++) {
                    const rotation = (i * 4 * Math.PI) / 5;
                    this.ctx.lineTo(
                        Math.cos(rotation) * 15,
                        Math.sin(rotation) * 15
                    );
                }
                this.ctx.closePath();
                this.ctx.fill();
                
                // Add glow effect
                this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
                this.ctx.lineWidth = 2;
                this.ctx.stroke();
                break;
        }
        
        this.ctx.restore();
    }

    drawPowerupIndicator(powerup) {
        // Draw powerup indicator in top-right corner
        const x = this.canvas.width - 120;
        const y = 30;
        
        // Background
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(x - 10, y - 20, 100, 40);
        
        // Powerup icon
        this.ctx.fillStyle = this.getPowerupColor(powerup.type);
        this.ctx.fillRect(x, y - 15, 20, 20);
        
        // Duration bar
        const remaining = powerup.duration / (powerup.original_duration || 5);
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        this.ctx.fillRect(x + 25, y - 5, 50, 10);
        
        this.ctx.fillStyle = this.getPowerupColor(powerup.type);
        this.ctx.fillRect(x + 25, y - 5, 50 * remaining, 10);
        
        // Text
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '12px Arial';
        this.ctx.fillText(powerup.type.toUpperCase(), x + 25, y + 15);
    }
    
    getPowerupColor(type) {
        switch(type) {
            case 'speed': return '#ff4444';
            case 'shield': return '#4444ff';
            case 'magnet': return '#ffff44';
            case 'time': return '#44ff44';
            default: return '#ffffff';
        }
    }

    handleServerUpdate(state) {
        this.gameState = state;
        
        // Check for game over
        if (state.game_over) {
            this.showGameOverScreen();
        }
        
        // Debug logging to track objects
        if (this.gameState.entities) {
            console.log(`Entities count: ${this.gameState.entities.length}`);
        }
        if (this.gameState.collectibles) {
            console.log(`Collectibles count: ${this.gameState.collectibles.length}`);
        }
    }
    
    showGameOverScreen() {
        const gameOverScreen = document.getElementById('game-over-screen');
        const finalScore = document.getElementById('final-score');
        const finalLevel = document.getElementById('final-level');
        
        if (gameOverScreen && finalScore && finalLevel) {
            finalScore.textContent = this.gameState.score || 0;
            finalLevel.textContent = this.gameState.level || 1;
            gameOverScreen.style.display = 'flex';
        }
    }
    
    hideGameOverScreen() {
        const gameOverScreen = document.getElementById('game-over-screen');
        if (gameOverScreen) {
            gameOverScreen.style.display = 'none';
        }
    }
    
    getPowerupColor(type) {
        switch(type) {
            case 'speed': return '#ff4444';
            case 'shield': return '#44ff44';
            case 'magnet': return '#4444ff';
            case 'time': return '#ffff44';
            default: return '#ff44ff';
        }
    }
}

// Global function for new game button
function startNewGame() {
    // Hide game over screen
    const gameOverScreen = document.getElementById('game-over-screen');
    if (gameOverScreen) {
        gameOverScreen.style.display = 'none';
    }
    
    // Request new game from server
    if (window.gameClient && window.gameClient.socket) {
        window.gameClient.socket.emit('new_game');
    } else {
        // Fallback to page reload if socket not available
        location.reload();
    }
}

// Initialize game when page loads
window.addEventListener('load', () => {
    window.gameClient = new GameClient();
});