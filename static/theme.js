function setTheme(themeName, labelText) {
    document.body.classList.remove('light-theme', 'birthday-theme', 'dark-theme');
    if (themeName !== 'dark-theme') {
        document.body.classList.add(themeName);
    }
    const statusLabel = document.getElementById('theme-status');
    if (statusLabel) { statusLabel.innerText = labelText; }
    localStorage.setItem('scardum-current-theme', themeName);
}

document.addEventListener("DOMContentLoaded", () => {
    const savedTheme = localStorage.getItem('scardum-current-theme') || 'dark-theme';
    if (savedTheme === 'light-theme') {
        if (document.getElementById('position-light')) document.getElementById('position-light').checked = true;
        setTheme('light-theme', 'LIGHT');
    } else if (savedTheme === 'birthday-theme') {
        if (document.getElementById('position-birthday')) document.getElementById('position-birthday').checked = true;
        setTheme('birthday-theme', 'BIRTHDAY');
    } else {
        if (document.getElementById('position-dark')) document.getElementById('position-dark').checked = true;
        setTheme('dark-theme', 'DARK');
    }
});