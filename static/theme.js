const THEMES = {
    'dark-theme':      { label: 'DARK',      position: 0 },
    'light-theme':     { label: 'LIGHT',     position: 1 },
    'vice-theme':      { label: 'VICE',      position: 2 },
    'halloween-theme': { label: 'HALLOWEEN', position: 3 },
};

// Окно доступности vice темы
function isViceThemeAvailable() {
    // ВРЕМЕННО РАСКОММЕНТИРУЙ СТРОКУ НИЖЕ ДЛЯ ТЕСТА ТЕМЫ VICE:
    // return true; 
    
    const now = new Date();
    const start = new Date('2026-11-19T00:00:00');
    const end   = new Date('2026-11-26T00:00:00');
    return now >= start && now < end;
}

// Хэллоуин-тема доступна с 25 октября по 2 ноября
function isHalloweenThemeAvailable() {
    const now = new Date();
    const month = now.getMonth();
    const day = now.getDate();
    if (month === 9 && day >= 25) return true;
    if (month === 10 && day <= 2) return true;
    return false;
}

function getAvailableThemes() {
    const available = ['dark-theme', 'light-theme'];
    if (isViceThemeAvailable()) available.push('vice-theme');
    if (isHalloweenThemeAvailable()) available.push('halloween-theme');
    return available;
}

// ==========================================
// ЭФФЕКТЫ ХЭЛЛОУИНА (Мыши и Паутина)
// ==========================================
let bats = [];
let batAnimationFrame = null;
let mouse = { x: -1000, y: -1000 };

function toggleHalloweenEffects(isActive) {
    let cobwebTL = document.querySelector('.halloween-cobweb.tl');
    let cobwebTR = document.querySelector('.halloween-cobweb.tr');

    if (isActive) {
        if (!cobwebTL) {
            cobwebTL = document.createElement('div');
            cobwebTL.className = 'halloween-cobweb tl';
            document.body.appendChild(cobwebTL);
        }
        if (!cobwebTR) {
            cobwebTR = document.createElement('div');
            cobwebTR.className = 'halloween-cobweb tr';
            document.body.appendChild(cobwebTR);
        }
        initBats();
    } else {
        removeBats();
    }
}

function initBats() {
    if (bats.length > 0) return; 
    
    if (batAnimationFrame) cancelAnimationFrame(batAnimationFrame);
    batAnimationFrame = null;

    const batCount = 20;
    for (let i = 0; i < batCount; i++) {
        const batEl = document.createElement('div');
        batEl.className = 'halloween-bat';
        
        const innerSpan = document.createElement('span');
        innerSpan.className = 'bat-icon';
        innerSpan.textContent = '🦇';
        batEl.appendChild(innerSpan);
        
        // Начальные позиции
        const x = Math.random() * window.innerWidth;
        const y = Math.random() * window.innerHeight;
        
        document.body.appendChild(batEl);
        
        bats.push({ 
            el: batEl, 
            x: x, 
            y: y, 
            size: 1 + Math.random() * 1.5,
            flapDuration: 0.3 + Math.random() * 0.3,
            // НОВОЕ: задаем угол полета и постоянную скорость
            angle: Math.random() * Math.PI * 2, 
            speed: 0.5 + Math.random() * 1.2, 
            wobble: Math.random() * Math.PI * 2 // для покачивания
        });
        
        innerSpan.style.animationDuration = `${bats[bats.length-1].flapDuration}s`;
    }
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseleave', onMouseLeave);
    animateBats();
}

function onMouseMove(e) {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
}

function onMouseLeave() {
    // Если мышь ушла за пределы окна, уводим её координаты далеко, чтобы мыши не прилипали
    mouse.x = -1000;
    mouse.y = -1000;
}

function animateBats() {
    const repelRadius = 150; 
    const repelForce = 2.5; // Усилили силу разлета от курсора
    
    bats.forEach(bat => {
        // 1. Плавно меняем направление (угол) со временем
        bat.angle += (Math.random() - 0.5) * 0.1;
        
        // 2. Вычисляем скорость на основе угла
        let vx = Math.cos(bat.angle) * bat.speed;
        let vy = Math.sin(bat.angle) * bat.speed;
        
        // 3. Отталкивание от курсора (если близко)
        const dx = bat.x - mouse.x;
        const dy = bat.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < repelRadius && dist > 0) {
            const force = (repelRadius - dist) / repelRadius;
            vx += (dx / dist) * force * repelForce;
            vy += (dy / dist) * force * repelForce;
            // Мышь пугается и меняет угол
            bat.angle = Math.atan2(vy, vx); 
        }
        
        // 4. Движение
        bat.x += vx;
        bat.y += vy;
        
        // 5. Телепорт на другую сторону, если улетел за экран
        if (bat.x < -50) bat.x = window.innerWidth + 50;
        if (bat.x > window.innerWidth + 50) bat.x = -50;
        if (bat.y < -50) bat.y = window.innerHeight + 50;
        if (bat.y > window.innerHeight + 50) bat.y = -50;
        
        // 6. Определяем, в какую сторону летит мышь
        if (Math.abs(vx) > 0.2) {
            bat.direction = vx > 0 ? -1 : 1; 
        }
        
        // 7. Эффект парения (мышь плавно покачивается вверх-вниз)
        bat.wobble += 0.1;
        const tilt = Math.sin(bat.wobble) * 15; 
        
        // 8. Применяем трансформации
        bat.el.style.transform = `translate3d(${bat.x}px, ${bat.y}px, 0) scale(${bat.size * bat.direction}, ${bat.size}) rotate(${tilt}deg)`;
    });
    
    batAnimationFrame = requestAnimationFrame(animateBats);
}

function removeBats() {
    if (batAnimationFrame) {
        cancelAnimationFrame(batAnimationFrame);
        batAnimationFrame = null;
    }
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseleave', onMouseLeave);
    
    bats.forEach(bat => bat.el.remove());
    bats = [];
    mouse = { x: -1000, y: -1000 };
}

// ==========================================
// ЭФФЕКТЫ VICE (GTA VI / Synthwave)
// ==========================================
let viceAnimationFrame;
let viceParticles = [];

function toggleViceEffects(isActive) {
    let grid = document.querySelector('.vice-grid');
    let sun = document.querySelector('.vice-sun-container');

    if (isActive) {
        if (!grid) {
            grid = document.createElement('div');
            grid.className = 'vice-grid';
            document.body.appendChild(grid);
        }
        if (!sun) {
            sun = document.createElement('div');
            sun.className = 'vice-sun-container';
            sun.innerHTML = '<div class="vice-sun"></div>';
            document.body.appendChild(sun);
        }
        initViceParticles();
    } else {
        if (grid) grid.remove();
        if (sun) sun.remove();
        stopViceParticles();
    }
}

function initViceParticles() {
    if (viceParticles.length > 0) return; 
    const colors = ['#ff2ea6', '#00e5ff', '#ff8c00', '#ffffff'];
    for (let i = 0; i < 30; i++) {
        const p = document.createElement('div');
        p.className = 'vice-particle';
        const size = Math.random() * 4 + 1; 
        p.style.width = `${size}px`;
        p.style.height = `${size}px`;
        const color = colors[Math.floor(Math.random() * colors.length)];
        p.style.backgroundColor = color;
        p.style.color = color; 
        p.style.left = `${Math.random() * 100}vw`;
        p.style.top = `${Math.random() * 100}vh`;
        p.dataset.speedY = 0.5 + Math.random() * 1.5; 
        p.dataset.drift = (Math.random() - 0.5) * 1;   
        document.body.appendChild(p);
        viceParticles.push(p);
    }
    animateViceParticles();
}

function animateViceParticles() {
    viceParticles.forEach(p => {
        let currentTop = parseFloat(p.style.top);
        let currentLeft = parseFloat(p.style.left);
        let speedY = parseFloat(p.dataset.speedY);
        let drift = parseFloat(p.dataset.drift);
        currentTop -= speedY;
        currentLeft += drift;
        if (currentTop < -10) {
            currentTop = 110;
            currentLeft = Math.random() * 100;
        }
        p.style.top = `${currentTop}vh`;
        p.style.left = `${currentLeft}vw`;
    });
    viceAnimationFrame = requestAnimationFrame(animateViceParticles);
}

function stopViceParticles() {
    cancelAnimationFrame(viceAnimationFrame);
    viceParticles.forEach(p => p.remove());
    viceParticles = [];
}

// ==========================================
// ОСНОВНАЯ ЛОГИКА ТЕМ
// ==========================================
function applyTheme(themeName) {
    const all = Object.keys(THEMES);
    all.forEach(t => document.body.classList.remove(t));

    const meta = THEMES[themeName];
    if (!meta) themeName = 'dark-theme';

    if (themeName !== 'dark-theme') {
        document.body.classList.add(themeName);
    }

    const status = document.getElementById('theme-status');
    if (status) status.innerText = THEMES[themeName].label;

    const input = document.getElementById('position-' + themeName.replace('-theme', ''));
    if (input) input.checked = true;

    const slider = document.querySelector('.triple-switch');
    if (slider) {
        slider.dataset.active = themeName;
        const availableThemes = getAvailableThemes();
        const actualPosition = availableThemes.indexOf(themeName);
        if (actualPosition !== -1) {
            slider.style.setProperty('--slider-pos', actualPosition);
        }
    }

    localStorage.setItem('scardum-current-theme', themeName);
    
    // ВКЛЮЧЕНИЕ/ВЫКЛЮЧЕНИЕ ЭФФЕКТОВ
    if (typeof toggleHalloweenEffects === 'function') {
        toggleHalloweenEffects(themeName === 'halloween-theme'); 
    }
    if (typeof toggleViceEffects === 'function') {
        toggleViceEffects(themeName === 'vice-theme');
    }
}

function setTheme(themeName) {
    const available = getAvailableThemes();
    if (!available.includes(themeName)) {
        applyTheme('dark-theme');
        return;
    }
    applyTheme(themeName);
}

document.addEventListener('DOMContentLoaded', () => {
    const available = getAvailableThemes();

    Object.keys(THEMES).forEach(t => {
        const key = t.replace('-theme', '');
        const input = document.getElementById('position-' + key);
        const label = document.querySelector('label[for="position-' + key + '"]');
        if (!input) return;
        const isAvailable = available.includes(t);
        input.classList.toggle('theme-hidden', !isAvailable);
        if (label) label.classList.toggle('theme-hidden', !isAvailable);
    });

    const slider = document.querySelector('.triple-switch');
    if (slider) {
        slider.style.setProperty('--slider-count', available.length);
    }

    let saved = localStorage.getItem('scardum-current-theme') || 'dark-theme';
    if (!available.includes(saved)) {
        saved = 'dark-theme';
    }

    if (isHalloweenThemeAvailable() && !localStorage.getItem('scardum-current-theme')) {
        saved = 'halloween-theme';
    }

    applyTheme(saved);
});