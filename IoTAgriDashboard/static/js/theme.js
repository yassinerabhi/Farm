// Theme switcher functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check for saved theme preference or respect OS preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
        // Apply saved theme
        document.documentElement.classList.toggle('dark-theme', savedTheme === 'dark');
        updateThemeIcon(savedTheme);
    } else {
        // Check if user's OS preference is dark
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
            document.documentElement.classList.add('dark-theme');
            updateThemeIcon('dark');
            localStorage.setItem('theme', 'dark');
        }
    }
    
    // Add event listener to theme switch button
    const themeSwitch = document.getElementById('theme-switch');
    if (themeSwitch) {
        themeSwitch.addEventListener('click', toggleTheme);
    }
    
    // Add event listener to sidebar toggle
    const sidebarToggle = document.getElementById('toggle-sidebar');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Add active class to current page in sidebar
    highlightCurrentPage();
});

function toggleTheme() {
    const root = document.documentElement;
    const isDark = root.classList.toggle('dark-theme');
    
    // Save preference
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    
    // Update icon
    updateThemeIcon(isDark ? 'dark' : 'light');
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
    }
}

function toggleSidebar() {
    const body = document.body;
    body.classList.toggle('collapsed-sidebar');
    
    // Save preference
    localStorage.setItem('sidebar', body.classList.contains('collapsed-sidebar') ? 'collapsed' : 'expanded');
    
    // Update icon
    const toggleIcon = document.getElementById('toggle-icon');
    if (toggleIcon) {
        if (body.classList.contains('collapsed-sidebar')) {
            toggleIcon.classList.remove('fa-angle-left');
            toggleIcon.classList.add('fa-angle-right');
        } else {
            toggleIcon.classList.remove('fa-angle-right');
            toggleIcon.classList.add('fa-angle-left');
        }
    }
}

function highlightCurrentPage() {
    // Get current path
    const currentPath = window.location.pathname;
    
    // Find matching menu item and add active class
    const menuItems = document.querySelectorAll('.sidebar-menu a');
    menuItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });
}

// Handle mobile sidebar
document.addEventListener('DOMContentLoaded', function() {
    // Check if mobile
    const isMobile = window.innerWidth < 768;
    
    if (isMobile) {
        // Collapse sidebar on mobile by default
        document.body.classList.add('collapsed-sidebar');
        
        // Show sidebar when toggle is clicked
        const toggleSidebar = document.getElementById('toggle-sidebar');
        const sidebar = document.querySelector('.sidebar');
        
        if (toggleSidebar && sidebar) {
            toggleSidebar.addEventListener('click', function() {
                sidebar.classList.toggle('show');
            });
            
            // Close sidebar when clicking outside
            document.addEventListener('click', function(event) {
                if (!sidebar.contains(event.target) && event.target !== toggleSidebar) {
                    sidebar.classList.remove('show');
                }
            });
        }
    } else {
        // For desktop, respect saved preference
        const savedSidebar = localStorage.getItem('sidebar');
        if (savedSidebar === 'collapsed') {
            document.body.classList.add('collapsed-sidebar');
            updateToggleIcon(true);
        }
    }
});

function updateToggleIcon(isCollapsed) {
    const toggleIcon = document.getElementById('toggle-icon');
    if (toggleIcon) {
        if (isCollapsed) {
            toggleIcon.classList.remove('fa-angle-left');
            toggleIcon.classList.add('fa-angle-right');
        } else {
            toggleIcon.classList.remove('fa-angle-right');
            toggleIcon.classList.add('fa-angle-left');
        }
    }
}
