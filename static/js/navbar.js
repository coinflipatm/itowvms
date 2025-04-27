/**
 * iTow Vehicle Management System - Navigation Bar Utilities
 * 
 * This script handles the navigation between different pages in the iTow system
 * and maintains active state for the current page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Set up navbar links
    setupNavigationLinks();
    
    // Highlight current page in navbar
    highlightCurrentPage();
    
    // Setup mobile navigation toggle if it exists
    setupMobileNav();
});

/**
 * Sets up click handlers for all navigation links
 */
function setupNavigationLinks() {
    // Regular navigation links
    document.querySelectorAll('.sidebar a').forEach(link => {
        link.addEventListener('click', function(e) {
            // If this is a page link (not a tab selector within a page)
            if (this.getAttribute('href') && this.getAttribute('href').startsWith('/')) {
                // Let the link handle navigation naturally
                return;
            }
            
            e.preventDefault();
            const tabName = this.dataset.tab;
            
            // If this is a navigation link to another page
            if (tabName === 'admin_users') {
                window.location.href = '/admin_users';
                return;
            } else if (tabName === 'create_invite') {
                window.location.href = '/create_invite';
                return;
            } else if (tabName === 'profile') {
                window.location.href = '/profile';
                return;
            } else if (tabName === 'logs') {
                window.location.href = '/logs';
                return;
            } else if (tabName === 'invitations') {
                window.location.href = '/invitations';
                return;
            }
            
            // For tabs within the main page
            document.querySelectorAll('.sidebar a').forEach(item => {
                item.classList.remove('active');
            });
            this.classList.add('active');
            
            // Update page title based on the clicked link
            document.getElementById('page-title').textContent = this.textContent.trim();
            
            // Hide all containers
            document.querySelectorAll('#vehicles-container, #notifications-container, #contacts-container, #statistics-container, #compliance-container')
                .forEach(container => container.classList.add('d-none'));
            
            // Show workflow counts by default for most tabs
            document.getElementById('workflow-counts').style.display = 'flex';
            document.getElementById('upcoming-actions-dashboard').style.display = 'block';
            
            // Show the appropriate container based on the tab
            if (tabName === 'notifications') {
                document.getElementById('notifications-container').classList.remove('d-none');
                loadPendingNotifications();
            } else if (tabName === 'contacts') {
                document.getElementById('contacts-container').classList.remove('d-none');
                loadContacts();
            } else if (tabName === 'statistics') {
                document.getElementById('statistics-container').classList.remove('d-none');
                document.getElementById('workflow-counts').style.display = 'none';
                document.getElementById('upcoming-actions-dashboard').style.display = 'none';
                updateStatistics();
            } else if (tabName === 'compliance') {
                document.getElementById('compliance-container').classList.remove('d-none');
                document.getElementById('workflow-counts').style.display = 'none';
                document.getElementById('upcoming-actions-dashboard').style.display = 'none';
                loadComplianceStatus();
            } else {
                document.getElementById('vehicles-container').classList.remove('d-none');
                loadVehicles(tabName);
            }
        });
    });
}

/**
 * Highlights the current page in the navbar based on URL
 */
function highlightCurrentPage() {
    const currentPath = window.location.pathname;
    
    // By default, activate the first link (active vehicles)
    let activeLink = document.querySelector('.sidebar a[data-tab="active"]');
    
    // Check if we're on a specific page
    if (currentPath === '/admin_users') {
        activeLink = document.querySelector('.sidebar a[data-tab="admin_users"]');
    } else if (currentPath === '/create_invite') {
        activeLink = document.querySelector('.sidebar a[data-tab="create_invite"]');
    } else if (currentPath === '/profile') {
        activeLink = document.querySelector('.sidebar a[data-tab="profile"]');
    } else if (currentPath === '/logs') {
        activeLink = document.querySelector('.sidebar a[data-tab="logs"]');
    } else if (currentPath === '/invitations') {
        activeLink = document.querySelector('.sidebar a[data-tab="invitations"]');
    }
    
    // Remove active class from all links
    document.querySelectorAll('.sidebar a').forEach(link => {
        link.classList.remove('active');
    });
    
    // Add active class to current page link
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

/**
 * Sets up mobile navigation toggle
 */
function setupMobileNav() {
    const mobileNavToggle = document.querySelector('.mobile-nav-toggle');
    if (mobileNavToggle) {
        mobileNavToggle.addEventListener('click', function() {
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.toggle('show-mobile');
        });
    }
}

/**
 * Updates the navigation bar with notification count
 * @param {number} count - Number of pending notifications
 */
function updateNotificationBadge(count) {
    const badge = document.getElementById('notification-count');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    }
}

// Add navigation links to the sidebar
function addNavigationLinks() {
    // This function can be used to dynamically add navigation links if needed
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    
    // Only add links that don't already exist
    if (!document.querySelector('.sidebar a[data-tab="profile"]')) {
        const profileLink = document.createElement('a');
        profileLink.href = "/profile";
        profileLink.dataset.tab = "profile";
        profileLink.innerHTML = '<i class="fas fa-user"></i> Profile';
        sidebar.appendChild(profileLink);
    }
    
    if (!document.querySelector('.sidebar a[data-tab="logs"]')) {
        const logsLink = document.createElement('a');
        logsLink.href = "/logs";
        logsLink.dataset.tab = "logs";
        logsLink.innerHTML = '<i class="fas fa-history"></i> System Logs';
        sidebar.appendChild(logsLink);
    }
    
    // Add admin links only for admin users
    const isAdmin = document.body.dataset.userRole === 'admin';
    if (isAdmin) {
        if (!document.querySelector('.sidebar a[data-tab="admin_users"]')) {
            const adminLink = document.createElement('a');
            adminLink.href = "/admin_users";
            adminLink.dataset.tab = "admin_users";
            adminLink.innerHTML = '<i class="fas fa-users-cog"></i> Manage Users';
            sidebar.appendChild(adminLink);
        }
        
        if (!document.querySelector('.sidebar a[data-tab="invitations"]')) {
            const invitationsLink = document.createElement('a');
            invitationsLink.href = "/invitations";
            invitationsLink.dataset.tab = "invitations";
            invitationsLink.innerHTML = '<i class="fas fa-envelope-open-text"></i> Invitations';
            sidebar.appendChild(invitationsLink);
        }
    }
}

// Call this function initially to add any missing navigation links
addNavigationLinks();