/**
 * Main.js - Core functionality for iTow Impound Manager
 * Handles tab switching, data loading, and basic UI interactions
 */

// Global authentication error handler
function handleAuthenticationError(response, error) {
    if (response && response.status === 401) {
        console.warn('Authentication error detected:', response.status);
        showToast('Your session has expired. Please log in again.', 'warning');
        
        // Show authentication help after a delay
        setTimeout(() => {
            if (confirm('Your session has expired. Would you like to reload the page to log in again?')) {
                window.location.reload();
            } else {
                showToast('You can also try refreshing the page (Ctrl+F5) or visit /auth-diagnostics for help', 'info');
            }
        }, 2000);
        return true;
    }
    
    if (error && (error.message.includes('Authentication required') || error.message.includes('401'))) {
        console.warn('Authentication error in message:', error.message);
        showToast('Authentication error. Please refresh the page and log in again.', 'warning');
        return true;
    }
    
    return false;
}

// Global fetch wrapper with authentication handling
async function authenticatedFetch(url, options = {}) {
    // Ensure credentials are included
    options.credentials = options.credentials || 'include';
    
    try {
        const response = await fetch(url, options);
        
        // Check for authentication errors
        if (response.status === 401) {
            handleAuthenticationError(response);
            throw new Error('Authentication required');
        }
        
        return response;
    } catch (error) {
        if (handleAuthenticationError(null, error)) {
            throw error;
        }
        throw error;
    }
}

// Global error handlers
window.addEventListener('error', function(event) {
    console.error('Global unhandled error:', event.message, event.filename, event.lineno, event.colno, event.error);
    // Attempt to ensure loading is hidden if an unexpected error occurs, as a fallback.
    const loader = document.getElementById('content-loader');
    if (loader && loader.style.display !== 'none') {
        console.warn('Global error handler: Forcing loader to hide due to unhandled error.');
        loader.style.display = 'none';
    }
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Global unhandled promise rejection:', event.reason);
    // Attempt to ensure loading is hidden, as a fallback.
    const loader = document.getElementById('content-loader');
    if (loader && loader.style.display !== 'none') {
        console.warn('Global unhandled promise rejection: Forcing loader to hide.');
        loader.style.display = 'none';
    }
});

// Global state for the application
const appState = {
    currentTab: 'dashboard',
    vehiclesData: [],
    lastVehicleTab: null, // Added for better vehicle data caching logic
    contactsData: [],
    notificationsData: [],
    isLoading: false,
    sortColumn: 'tow_date',
    sortDirection: 'desc',
    lastLoadingToggleTime: 0, // Used for detecting rapid toggles
};

// Initialize on document load
document.addEventListener('DOMContentLoaded', function() {
    console.log('iTow Manager: DOMContentLoaded. Initializing application...'); // Logging
    
    try {
        setupTabHandlers();
        initializeTooltips(); // Ensure Bootstrap JS is loaded before this
        checkNotifications(); // Async, should not block
        console.log("Initial call to loadTab('dashboard')"); // Logging
        loadTab('dashboard'); // This is the main entry point for content loading
    } catch (e) {
        console.error("Error during initial setup in DOMContentLoaded:", e);
        hideLoading(); // Try to hide if it was somehow shown
        const body = document.body;
        if (body) {
            body.innerHTML = `<div class="alert alert-danger m-5">A critical error occurred during application startup. Please check the console. Error: ${e.message}</div>`;
        }
    }
    
    // Set up refresh button if present
    const refreshBtn = document.getElementById('refresh-data');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadTab(appState.currentTab, true); // Force refresh
        });
    }
    
    // Start periodic data refresh
    setInterval(refreshCurrentTab, 60000); // Refresh every minute
});

/**
 * Set up click handlers for sidebar tabs
 */
function setupTabHandlers() {
    console.log("Setting up tab handlers..."); // Log when this function runs
    document.querySelectorAll('.sidebar a[data-tab]').forEach(link => {
        const href = link.getAttribute('href');
        const tabName = link.dataset.tab;

        if (href === '#') {
            link.addEventListener('click', function(e) {
                console.log(`Tab link '${tabName}' (href='#') clicked.`); // Log click
                e.preventDefault(); // Explicitly call first
                console.log(`preventDefault() called for '${tabName}'.`);

                loadTab(tabName); // Load the tab content

                // Special case: scraper tab should open the import modal
                if (tabName === 'scraper') {
                    const importModalElement = document.getElementById('importVehiclesModal');
                    if (importModalElement) {
                        // Ensure Bootstrap's Modal class is available
                        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                            const importModal = new bootstrap.Modal(importModalElement);
                            importModal.show();
                        } else {
                            console.error("Bootstrap Modal class not found. Cannot open scraper modal.");
                        }
                    } else {
                        console.error("Import vehicles modal element not found for scraper tab.");
                    }
                }
            });
            console.log(`Added click listener for tab '${tabName}' (href='#')`);
        } else if (href && href.startsWith('/')) {
            // This handles links like /logout or any other full page navigation links in the sidebar
            console.log(`Skipping client-side handler for tab '${tabName}' (href='${href}'), allowing default browser navigation.`);
            // No event listener added here, so browser handles it (e.g., for /logout)
        } else {
            console.warn(`Sidebar link for tab '${tabName}' has an unexpected href: '${href}'. It might not be handled correctly.`);
        }
    });
}

/**
 * Load content for the selected tab
 * @param {string} tabName - The name of the tab to load
 * @param {boolean} forceRefresh - Whether to force a data refresh
 */
function loadTab(tabName, forceRefresh = false) {
    console.log(`Loading tab: ${tabName}`); // Existing LOG
    
    // Update active tab state in sidebar
    document.querySelectorAll('.sidebar a[data-tab]').forEach(link => {
        link.classList.remove('active');
    });
    const activeTabLink = document.querySelector(`.sidebar a[data-tab="${tabName}"]`);
    if (activeTabLink) {
        activeTabLink.classList.add('active');
        console.log(`Set tab '${tabName}' as active in sidebar.`); // ADDED LOG
    } else {
        console.warn(`Could not find sidebar link for tab '${tabName}' to set active class.`); // ADDED LOG
    }
    
    // Update current tab in state - MOVED this line earlier, was after activeTabLink handling
    appState.currentTab = tabName; 
    console.log(`appState.currentTab set to: ${appState.currentTab}`); // ADDED LOG
    
    // Update page title
    updatePageTitle(tabName);
    
    // Show loading indicator
    showLoading();
    
    // Load appropriate content based on tab
    switch (tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'active': // This is a general filter, not a specific status
        case 'New':
        case 'TOP_Generated':
        case 'Ready_for_Auction':
        case 'Ready_for_Scrap':
        case 'completed': // This is also a general filter
            loadVehicles(tabName, forceRefresh);
            break;
        case 'notifications':
            loadNotifications(forceRefresh);
            break;
        case 'contacts':
            loadContacts(forceRefresh);
            break;
        case 'reports':
            loadReports();
            break;
        case 'statistics':
            loadStatistics(); // Ensure this calls the new rendering logic
            break;
        case 'compliance':
            loadCompliance();
            break;
        case 'profile': // New case
            loadProfile();
            break;
        case 'logs': // New case
            loadLogs();
            break;
        default:
            // For any other tab, show a placeholder message
            document.getElementById('dynamic-content-area').innerHTML = 
                `<div class="alert alert-info">Content for "${tabName}" is being developed.</div>`;
            hideLoading();
    }
}

/**
 * Update the page title based on the selected tab
 */
function updatePageTitle(tabName) {
    const titleElement = document.getElementById('current-tab-title');
    if (!titleElement) return;
    
    const activeTab = document.querySelector(`.sidebar a[data-tab="${tabName}"]`);
    if (activeTab) {
        // Use tooltip content if available, otherwise use the text content
        const title = activeTab.getAttribute('data-bs-original-title') || 
                      activeTab.getAttribute('title') || 
                      activeTab.textContent.trim();
        titleElement.textContent = title;
    } else {
        titleElement.textContent = tabName.charAt(0).toUpperCase() + tabName.slice(1);
    }
}

/**
 * Refresh the current tab's data
 */
function refreshCurrentTab() {
    if (!appState.isLoading) { // Prevent multiple simultaneous refreshes
        loadTab(appState.currentTab, true);
    }
}

/**
 * Show loading indicator
 */
let showLoadingCallCount = 0;
const contentLoaderId = 'content-loader'; // Ensure this is consistently defined and used

function showLoading(message = 'Loading...') {
    showLoadingCallCount++;
    console.log(`showLoading called (${showLoadingCallCount} times). Message: ${message}. Current appState.isLoading: ${appState.isLoading}`);

    if (appState.isLoading && showLoadingCallCount > 1 && (performance.now() - appState.lastLoadingToggleTime < 100)) {
        console.warn(`showLoading called rapidly or while already loading. Call stack:`, new Error().stack);
    }
    appState.isLoading = true;
    appState.lastLoadingToggleTime = performance.now();

    let loader = document.getElementById(contentLoaderId);
    if (!loader) {
        console.log('showLoading: Loader element not found, creating it.');
        loader = document.createElement('div');
        loader.id = contentLoaderId;
        loader.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        loader.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';
        loader.style.zIndex = '1050'; // Ensure it's a high z-index
        loader.innerHTML = `
            <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                <span class="visually-hidden">${message}</span>
            </div>
            <p class="ms-2 mb-0 text-primary" id="loading-message">${message}</p>`;
        document.body.appendChild(loader);
        console.log('showLoading: Loader element created and appended to body.');
    } else {
        console.log(`showLoading: Loader element found. Current display style: '${loader.style.display}'.`);
        if (loader.style.display === 'none') {
            console.warn('showLoading: Re-showing a loader that was previously hidden.');
        }
        const loadingMessageElement = loader.querySelector('#loading-message');
        if (loadingMessageElement) {
            loadingMessageElement.textContent = message;
        }
    }
    loader.style.display = 'flex';
    // Truncate outerHTML log for brevity if it's too long
    const loaderOuterHTML = loader.outerHTML;
    console.log(`showLoading: Loader display style set to 'flex'. Loader outerHTML: ${loaderOuterHTML.substring(0, 300)}${loaderOuterHTML.length > 300 ? '...' : ''}`);
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    console.log(`hideLoading called. appState.isLoading was: ${appState.isLoading}`);
    appState.isLoading = false;
    appState.lastLoadingToggleTime = performance.now();

    const loader = document.getElementById(contentLoaderId);
    if (loader) {
        console.log(`hideLoading: Loader element found. Current display style: '${loader.style.display}'. Removing it from the DOM.`);
        loader.remove(); // Remove the element entirely
        
        // Confirm removal by trying to get it again
        const stillExists = document.getElementById(contentLoaderId);
        console.log(`hideLoading: Loader element after removal attempt. Check if still exists in DOM: ${stillExists === null ? 'No (Successfully removed)' : 'Yes (Removal somehow failed!)'}`);
        if (stillExists) {
            // This case should be highly unlikely if loader.remove() works as expected.
            console.error(`hideLoading: FAILED to remove loader element from DOM. Element outerHTML: ${stillExists.outerHTML.substring(0,300)}...`);
            // As a fallback, try to hide it aggressively if removal failed
            stillExists.style.display = 'none !important'; 
        }
    } else {
        console.log('hideLoading: Loader element not found (already removed or never created). Cannot remove.');
    }
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(tooltipTriggerEl => {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Check for pending notifications
 */
async function checkNotifications() { // Made async
    try {
        const response = await fetch('/api/notifications/pending-count'); // Changed endpoint
        if (!response.ok) {
            console.error('Error fetching notification count:', response.status, response.statusText);
            const errorData = await response.json().catch(() => null); // Try to get error details
            showToast(`Error fetching notifications: ${errorData?.error || response.statusText}`, 'error');
            return;
        }
        const data = await response.json();
        const count = data.pending_count; // Assuming the API returns { pending_count: X }
        const badge = document.getElementById('notification-count');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.classList.remove('d-none');
            } else {
                badge.textContent = '0'; // Show 0 instead of hiding
                badge.classList.add('d-none'); // Or keep it hidden if 0
            }
        }
    } catch (error) {
        console.error('Error in checkNotifications:', error);
        showToast('Could not check for new notifications.', 'error');
    }
}

/**
 * Load dashboard data and render dashboard view
 */
function loadDashboard() {
    console.log("loadDashboard called"); // Logging
    // showLoading() is called by loadTab before this function

    fetch('/api/workflow-counts')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Workflow counts API request failed: ${response.status} ${response.statusText}`);
            }
            return response.json().catch(jsonError => {
                console.error('Failed to parse JSON for workflow-counts:', jsonError);
                // Attempt to get text for more context if JSON parsing fails
                return response.text().then(text => {
                    console.error('Response text for failed workflow-counts JSON:', text);
                    throw new Error('Invalid JSON response from workflow-counts API. See console for response text.');
                });
            });
        })
        .then(workflowData => {
            return fetch('/api/statistics')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Statistics API request failed: ${response.status} ${response.statusText}`);
                    }
                    return response.json().catch(jsonError => {
                        console.error('Failed to parse JSON for statistics:', jsonError);
                        return response.text().then(text => {
                            console.error('Response text for failed statistics JSON:', text);
                            throw new Error('Invalid JSON response from statistics API. See console for response text.');
                        });
                    });
                })
                .then(statsData => {
                    console.log("Data fetched, calling renderDashboard"); // Logging
                    renderDashboard(workflowData, statsData);
                });
        })
        .catch(error => {
            console.error('Error in loadDashboard promise chain:', error);
            const dynamicContentArea = document.getElementById('dynamic-content-area');
            if (dynamicContentArea) {
                dynamicContentArea.innerHTML = `
                  <div class="alert alert-danger">
                      Failed to load dashboard data: ${error.message}. Check console for details.
                  </div>`;
            }
        })
        .finally(() => {
            console.log("loadDashboard finally block: calling hideLoading()"); // Logging
            hideLoading();
        });
}

/**
 * Render the dashboard with workflow counts and statistics
 */
function renderDashboard(workflowCounts, statisticsData) { // Removed pendingNotifications as it's not directly used here
    console.log('renderDashboard called with data:', { workflowCounts, statisticsData });
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    if (!dynamicContentArea) {
        console.error('renderDashboard: Dynamic content area not found!');
        return; // Exit if the main content area isn't there
    }

    // Basic user info - replace with actual user data if available in appState
    const userName = appState.currentUser ? appState.currentUser.username : 'User';

    let dashboardHtml = `
        <div class="container-fluid pt-3">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2">Dashboard</h1>
                <div class="btn-toolbar mb-2 mb-md-0">
                    <div class="btn-group me-2">
                        <button type="button" class="btn btn-sm btn-outline-secondary">Share</button>
                        <button type="button" class="btn btn-sm btn-outline-secondary">Export</button>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-secondary dropdown-toggle">
                        <span data-feather="calendar"></span>
                        This week
                    </button>
                </div>
            </div>
            <p>Welcome back, ${userName}!</p>

            <!-- Workflow Counts Row -->
            <div class="row">
                ${Object.entries(workflowCounts || {}).map(([status, count]) => `
                    <div class="col-md-3 col-sm-6 mb-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">${status.replace(/_/g, ' ')}</h5>
                                <p class="card-text fs-2">${count}</p>
                            </div>
                        </div>
                    </div>
                `).join('')}
                ${(Object.keys(workflowCounts || {}).length === 0) ? '<p class="text-muted">Workflow counts are currently unavailable.</p>' : ''}
            </div>

            <!-- Charts Row -->
            <div class="row mt-3">
                <div class="col-lg-4 col-md-6 mb-3">
                    <div class="card h-100">
                        <div class="card-header">Status Distribution</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <canvas id="statusDistributionChart" style="display: none;"></canvas>
                            <p id="statusDistributionMessage" class="text-center m-0"></p>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4 col-md-6 mb-3">
                    <div class="card h-100">
                        <div class="card-header">Average Processing Time</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <canvas id="avgProcessingTimeChart" style="display: none;"></canvas>
                            <p id="avgProcessingTimeMessage" class="text-center m-0"></p>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4 col-md-12 mb-3"> <!-- Changed to col-md-12 to take full width on medium if others are small -->
                    <div class="card h-100">
                        <div class="card-header">Jurisdiction Distribution</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <canvas id="jurisdictionPieChartDashboard" style="display: none;"></canvas>
                            <p id="jurisdictionPieChartMessage" class="text-center m-0"></p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Pending Notifications Section -->
            <div class="row mt-3">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">Pending Notifications</div>
                        <div class="card-body">
                            <ul id="pendingNotificationsList" class="list-group">
                                <!-- Notifications will be listed here -->
                            </ul>
                            <p id="pendingNotificationsMessage" class="text-center"></p>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    dynamicContentArea.innerHTML = dashboardHtml;
    console.log('renderDashboard: Initial HTML structure rendered.');

    // Feather icons (if you use them)
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Render Pending Notifications
    const notificationsList = document.getElementById('pendingNotificationsList');
    const notificationsMsg = document.getElementById('pendingNotificationsMessage');
    if (pendingNotifications && pendingNotifications.length > 0) {
        notificationsList.innerHTML = pendingNotifications.map(n => `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                Vehicle ${n.license_plate || n.vehicle_id} - ${n.notification_type} for ${n.recipient}
                <span class="badge bg-warning rounded-pill">${new Date(n.due_date).toLocaleDateString()}</span>
            </li>`).join('');
        notificationsMsg.textContent = '';
    } else {
        console.log('No pending notifications to display on dashboard.');
        notificationsMsg.textContent = 'No pending notifications.';
        if (notificationsList) notificationsList.innerHTML = ''; // Clear any previous items
    }

    // Chart rendering logic with explicit messages and canvas visibility toggle
    const statusCtx = document.getElementById('statusDistributionChart');
    const statusMsg = document.getElementById('statusDistributionMessage');
    try {
        if (statisticsData && statisticsData.status_distribution && Object.keys(statisticsData.status_distribution).length > 0) {
            console.log('Rendering status distribution chart with data:', statisticsData.status_distribution);
            if(statusCtx) statusCtx.style.display = 'block';
            if(statusMsg) statusMsg.textContent = '';
            new Chart(statusCtx, {
                type: 'pie',
                data: {
                    labels: Object.keys(statisticsData.status_distribution),
                    datasets: [{
                        label: 'Status Distribution',
                        data: Object.values(statisticsData.status_distribution),
                        backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6c757d'],
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        } else {
            console.log('No status distribution data to render chart.');
            if(statusCtx) statusCtx.style.display = 'none';
            if(statusMsg) statusMsg.textContent = 'Status distribution data is currently unavailable.';
        }
    } catch (e) {
        console.error('Error rendering status distribution chart:', e);
        if(statusCtx) statusCtx.style.display = 'none';
        if(statusMsg) statusMsg.textContent = 'Error displaying status chart.';
    }

    const avgTimeCtx = document.getElementById('avgProcessingTimeChart');
    const avgTimeMsg = document.getElementById('avgProcessingTimeMessage');
     try {
        if (statisticsData && statisticsData.average_processing_times && Object.keys(statisticsData.average_processing_times).length > 0) {
            console.log('Rendering average processing time chart with data:', statisticsData.average_processing_times);
            if(avgTimeCtx) avgTimeCtx.style.display = 'block';
            if(avgTimeMsg) avgTimeMsg.textContent = '';
            new Chart(avgTimeCtx, {
                type: 'bar',
                data: {
                    labels: Object.keys(statisticsData.average_processing_times),
                    datasets: [{
                        label: 'Avg. Days',
                        data: Object.values(statisticsData.average_processing_times).map(d => parseFloat(d) || 0),
                        backgroundColor: '#17a2b8',
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
            });
        } else {
            console.log('No average processing time data to render chart.');
            if(avgTimeCtx) avgTimeCtx.style.display = 'none';
            if(avgTimeMsg) avgTimeMsg.textContent = 'Average processing time data is currently unavailable.';
        }
    } catch (e) {
        console.error('Error rendering average processing time chart:', e);
        if(avgTimeCtx) avgTimeCtx.style.display = 'none';
        if(avgTimeMsg) avgTimeMsg.textContent = 'Error displaying processing time chart.';
    }

    const jurCtx = document.getElementById('jurisdictionPieChartDashboard');
    const jurMsg = document.getElementById('jurisdictionPieChartMessage');
    try {
        if (statisticsData && statisticsData.jurisdiction_distribution && Object.keys(statisticsData.jurisdiction_distribution).length > 0) {
            console.log('Rendering jurisdiction pie chart with data:', statisticsData.jurisdiction_distribution);
            if(jurCtx) jurCtx.style.display = 'block';
            if(jurMsg) jurMsg.textContent = '';
            new Chart(jurCtx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(statisticsData.jurisdiction_distribution),
                    datasets: [{
                        label: 'Jurisdiction',
                        data: Object.values(statisticsData.jurisdiction_distribution),
                        backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6f42c1', '#20c997'],
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        } else {
            console.log('No jurisdiction distribution data to render chart on dashboard.');
            if(jurCtx) jurCtx.style.display = 'none';
            if(jurMsg) jurMsg.textContent = 'Jurisdiction distribution data is currently unavailable.';
        }
    } catch (e) {
        console.error('Error rendering jurisdiction pie chart:', e);
        if(jurCtx) jurCtx.style.display = 'none';
        if(jurMsg) jurMsg.textContent = 'Error displaying jurisdiction chart.';
    }
    console.log('renderDashboard completed all rendering tasks.');
}

// Placeholder for Profile tab
function loadProfile() {
    console.log("loadProfile called");
    // showLoading() is called by loadTab.
    // Actual data fetching would be async.
    try {
        renderProfile();
    } catch (e) {
        console.error("Error rendering profile:", e);
        const dynamicContentArea = document.getElementById('dynamic-content-area');
        if (dynamicContentArea) {
            dynamicContentArea.innerHTML = `<div class="alert alert-danger">Error loading profile content: ${e.message}</div>`;
        }
    } finally {
        hideLoading();
    }
}

function renderProfile() {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    if (dynamicContentArea) {
        dynamicContentArea.innerHTML = `
            <div class="container mt-4">
                <h2>User Profile</h2>
                <p>This is the user profile page. Content to be added.</p>
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Profile Details</h5>
                        <p>Username: <span id="profile-username">DemoUser</span></p>
                        <p>Email: <span id="profile-email">demo@example.com</span></p>
                        <button class="btn btn-primary">Edit Profile</button>
                    </div>
                </div>
            </div>
        `;
    } else {
        console.error("dynamic-content-area not found for profile");
    }
}

// Placeholder for Logs tab
function loadLogs() {
    console.log("loadLogs called");
    // showLoading() is called by loadTab.
    try {
        renderLogs(); 
    } catch (e) {
        console.error("Error rendering logs:", e);
        const dynamicContentArea = document.getElementById('dynamic-content-area');
        if (dynamicContentArea) {
            dynamicContentArea.innerHTML = `<div class="alert alert-danger">Error loading logs content: ${e.message}</div>`;
        }
    } finally {
        hideLoading();
    }
}

function renderLogs() {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    if (dynamicContentArea) {
        dynamicContentArea.innerHTML = `
            <div class="container mt-4">
                <h2>System Logs</h2>
                <p>This is the system logs page. Content to be added.</p>
                <div class="card">
                    <div class="card-header">
                        Log Entries (Placeholder)
                    </div>
                    <div class="card-body" style="max-height: 500px; overflow-y: auto;">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">[YYYY-MM-DD HH:MM:SS] INFO: Application started.</li>
                            <li class="list-group-item">[YYYY-MM-DD HH:MM:SS] DEBUG: Dashboard loaded for user.</li>
                            <li class="list-group-item">[YYYY-MM-DD HH:MM:SS] WARN: Low disk space warning.</li>
                            <li class="list-group-item">[YYYY-MM-DD HH:MM:SS] ERROR: Failed to connect to external service.</li>
                        </ul>
                    </div>
                    <div class="card-footer">
                        <button class="btn btn-sm btn-secondary" onclick="loadLogs()">Refresh Logs</button>
                    </div>
                </div>
            </div>
        `;
    } else {
        console.error("dynamic-content-area not found for logs");
    }
}

/**
 * Load vehicles data for the specified status tab
 */
function loadVehicles(statusFilter = 'active', forceRefresh = false) {
    console.log(`loadVehicles called with statusFilter: ${statusFilter}, forceRefresh: ${forceRefresh}`);
    showLoading('Loading vehicles...');

    // Convert tab name to proper status filter
    const apiStatusFilter = convertTabNameToStatusFilter(statusFilter);
    console.log(`Converted ${statusFilter} to ${apiStatusFilter} for API call`);

    // If data for this specific filter is already loaded and not forcing refresh, use it.
    // This simple cache assumes `appState.vehiclesData` holds data for the *last loaded* filter.
    // A more sophisticated cache would store data per filter.
    if (appState.vehiclesData.length > 0 && appState.lastVehicleTab === statusFilter && !forceRefresh) {
        console.log(`Using cached vehicle data for ${statusFilter}.`);
        renderVehicleTable(appState.vehiclesData, statusFilter);
        hideLoading();
        return;
    }

    let apiUrl = '/api/vehicles';
    // Construct the API URL with the status filter
    // 'active' can be the default or explicitly passed
    // 'completed' should be explicitly passed
    // Specific statuses (New, TOP_Generated, etc.) are passed directly
    if (apiStatusFilter) {
        apiUrl += `?status=${encodeURIComponent(apiStatusFilter)}`;
    }
    // Add sorting parameters
    apiUrl += `${apiStatusFilter ? '&' : '?'}sort=${appState.sortColumn}&direction=${appState.sortDirection}`;


    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(`Fetched ${data.length} vehicles for filter '${statusFilter}'.`);
            appState.vehiclesData = data;
            appState.lastVehicleTab = statusFilter; // Update the last loaded vehicle tab
            renderVehicleTable(data, statusFilter);
        })
        .catch(error => {
            console.error(`Error loading vehicles for filter '${statusFilter}':`, error);
            document.getElementById('dynamic-content-area').innerHTML = 
                `<div class="alert alert-danger">Failed to load vehicles: ${error.message}</div>`;
        })
        .finally(() => {
            hideLoading();
        });
}

/**
 * Render the vehicle table
 * @param {Array} vehicles - Array of vehicle objects
 * @param {string} currentFilterName - The name of the current filter/tab
 */
function renderVehicleTable(vehicles, currentFilterName) {
    console.log(`renderVehicleTable called for filter: ${currentFilterName} with ${vehicles.length} vehicles.`);
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    if (!dynamicContentArea) {
        console.error('Dynamic content area not found for rendering vehicle table.');
        return;
    }

    // Clear previous content
    dynamicContentArea.innerHTML = ''; 

    // Add header with Add Vehicle button
    const headerDiv = document.createElement('div');
    headerDiv.className = 'd-flex justify-content-between align-items-center mb-3';
    
    const titleDiv = document.createElement('div');
    const title = document.createElement('h4');
    title.textContent = `Vehicles - ${currentFilterName.charAt(0).toUpperCase() + currentFilterName.slice(1)} (${vehicles.length})`;
    titleDiv.appendChild(title);
    
    const buttonDiv = document.createElement('div');
    const addButton = document.createElement('button');
    addButton.className = 'btn btn-primary';
    addButton.innerHTML = '<i class="fas fa-plus"></i> Add Vehicle';
    addButton.onclick = showAddVehicleModal;
    buttonDiv.appendChild(addButton);
    
    headerDiv.appendChild(titleDiv);
    headerDiv.appendChild(buttonDiv);
    dynamicContentArea.appendChild(headerDiv);

    // Create table structure
    const table = document.createElement('table');
    table.className = 'table table-striped table-hover vehicle-table'; // Added table-hover for better UX

    // Table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const headers = [
        { key: 'towbook_call_number', text: 'Call #' },
        { key: 'complaint_number', text: 'Complaint #' },
        { key: 'vin', text: 'VIN' },
        { key: 'year', text: 'Year' },
        { key: 'make', text: 'Make' },
        { key: 'model', text: 'Model' },
        { key: 'color', text: 'Color' },
        { key: 'tow_date', text: 'Tow Date' },
        { key: 'status', text: 'Status' },
        { key: 'days_in_lot', text: 'Days' }, // Added Days in Lot
        { key: 'actions', text: 'Actions' }
    ];

    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header.text;
        th.dataset.column = header.key;
        // Add sorting class if this column is currently sorted
        if (appState.sortColumn === header.key) {
            th.classList.add(appState.sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }
        th.addEventListener('click', () => sortTableByColumn(header.key));
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Table body
    const tbody = document.createElement('tbody');
    if (vehicles.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = headers.length;
        td.textContent = 'No vehicles found matching this criteria.';
        td.className = 'text-center';
        tr.appendChild(td);
        tbody.appendChild(tr);
    } else {
        vehicles.forEach(vehicle => {
            const tr = document.createElement('tr');
            tr.dataset.vehicleId = vehicle.towbook_call_number; // Store vehicle call number for actions

            // Order of cells should match headers
            const cells = [
                vehicle.towbook_call_number || 'N/A',
                vehicle.complaint_number || 'N/A',
                vehicle.vin || 'N/A',
                vehicle.year || 'N/A',
                vehicle.make || 'N/A',
                vehicle.model || 'N/A',
                vehicle.color || 'N/A',
                formatDateForDisplay(vehicle.tow_date), // Use consistent date formatting
                renderStatusLabel(vehicle.status), // Use a helper for status
                calculateDaysInLot(vehicle.tow_date), // Calculate days in lot
                renderActionButtons(vehicle) // Use a helper for action buttons
            ];

            cells.forEach(cellContent => {
                const td = document.createElement('td');
                if (typeof cellContent === 'string') {
                    td.textContent = cellContent;
                } else { // If it's an HTML element (like status label or buttons)
                    td.appendChild(cellContent);
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }
    table.appendChild(tbody);
    dynamicContentArea.appendChild(table);
    console.log('Vehicle table rendered.');
}

/**
 * Helper function to render a status label
 * @param {string} status - The status string
 * @returns {HTMLElement} - A span element with the status label
 */
function renderStatusLabel(status) {
    const span = document.createElement('span');
    span.className = `status-label status-${status ? status.toLowerCase().replace(/_/g, '-') : 'unknown'}`;
    span.textContent = status || 'Unknown';
    return span;
}

/**
 * Helper function to calculate days in lot
 * @param {string} towDateStr - The tow date as a string
 * @returns {string} - Number of days in lot or 'N/A'
 */
function calculateDaysInLot(towDateStr) {
    if (!towDateStr) return 'N/A';
    
    let towDate;
    
    // Handle YYYY-MM-DD format specifically to avoid timezone issues
    if (/^\d{4}-\d{2}-\d{2}$/.test(towDateStr)) {
        const [year, month, day] = towDateStr.split('-');
        towDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    } else {
        towDate = new Date(towDateStr);
    }
    
    if (isNaN(towDate.getTime())) return 'N/A';
    
    const today = new Date();
    // Set both dates to midnight for accurate day calculation
    towDate.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);
    
    const diffTime = today - towDate;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    const span = document.createElement('span');
    span.textContent = diffDays;
    span.className = 'days-counter';
    if (diffDays > 30) span.classList.add('critical'); // Example: critical after 30 days
    else if (diffDays > 15) span.classList.add('warning'); // Example: warning after 15 days
    return span;
}

/**
 * Helper function to render action buttons for a vehicle
 * @param {object} vehicle - The vehicle object
 * @returns {HTMLElement} - A div containing action buttons
 */
function renderActionButtons(vehicle) {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'action-links';

    // View Details Button
    const viewButton = document.createElement('a');
    viewButton.href = '#';
    viewButton.innerHTML = '<i class="fas fa-eye"></i>';
    viewButton.title = 'View Details';
    viewButton.onclick = (e) => { e.preventDefault(); openVehicleDetailsModal(vehicle.towbook_call_number); };
    actionsDiv.appendChild(viewButton);

    // Edit Button
    const editButton = document.createElement('a');
    editButton.href = '#';
    editButton.innerHTML = '<i class="fas fa-edit"></i>';
    editButton.title = 'Edit Vehicle';
    editButton.onclick = (e) => { e.preventDefault(); openEditVehicleModal(vehicle.towbook_call_number); };
    actionsDiv.appendChild(editButton);

    // Delete Button
    const deleteButton = document.createElement('a');
    deleteButton.href = '#';
    deleteButton.innerHTML = '<i class="fas fa-trash"></i>';
    deleteButton.title = 'Delete Vehicle';
    deleteButton.className = 'text-danger';
    deleteButton.onclick = (e) => { e.preventDefault(); deleteVehicle(vehicle.towbook_call_number); };
    actionsDiv.appendChild(deleteButton);

    // Generate Forms Dropdown
    const formsDropdownContainer = document.createElement('div');
    formsDropdownContainer.className = 'dropdown d-inline-block'; // d-inline-block for proper alignment

    const formsButton = document.createElement('button');
    formsButton.className = 'btn btn-sm btn-outline-secondary dropdown-toggle';
    formsButton.type = 'button';
    formsButton.id = `formsDropdown-${vehicle.towbook_call_number}`;
    formsButton.setAttribute('data-bs-toggle', 'dropdown');
    formsButton.setAttribute('aria-expanded', 'false');
    formsButton.innerHTML = '<i class="fas fa-file-alt"></i> Forms';
    formsButton.title = 'Generate Forms';

    const dropdownMenu = document.createElement('ul');
    dropdownMenu.className = 'dropdown-menu';
    dropdownMenu.setAttribute('aria-labelledby', `formsDropdown-${vehicle.towbook_call_number}`);

    // Define available forms (only TOP and Release Notice)
    const availableForms = [
        { name: 'TOP', endpoint: 'generate-top', condition: true },
        { name: 'Release Notice', endpoint: 'generate-release-notice', condition: true }
    ];

    availableForms.forEach(form => {
        if (form.condition) {
            const listItem = document.createElement('li');
            const link = document.createElement('a');
            link.className = 'dropdown-item';
            link.href = '#';
            link.textContent = `Generate ${form.name}`;
            link.onclick = (e) => { 
                e.preventDefault(); 
                generateDocumentApiCall(vehicle.towbook_call_number, form.endpoint, form.name);
            };
            listItem.appendChild(link);
            dropdownMenu.appendChild(listItem);
        }
    });

    if (dropdownMenu.children.length > 0) {
        formsDropdownContainer.appendChild(formsButton);
        formsDropdownContainer.appendChild(dropdownMenu);
        actionsDiv.appendChild(formsDropdownContainer);
    } else {
        // Optionally, show a disabled-like button or nothing if no forms are available
        const noFormsButton = document.createElement('button');
        noFormsButton.className = 'btn btn-sm btn-outline-secondary';
        noFormsButton.innerHTML = '<i class="fas fa-file-alt"></i> Forms';
        noFormsButton.title = 'No forms available for current status';
        noFormsButton.disabled = true;
        actionsDiv.appendChild(noFormsButton);
    }

    return actionsDiv;
}

/**
 * Sorts the vehicle table by a given column
 * @param {string} columnKey - The key of the column to sort by
 */
function sortTableByColumn(columnKey) {
    if (appState.sortColumn === columnKey) {
        appState.sortDirection = appState.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        appState.sortColumn = columnKey;
        appState.sortDirection = 'asc';
    }

    // Sort the data
    appState.vehiclesData.sort((a, b) => {
        let valA = a[columnKey];
        let valB = b[columnKey];

        // Handle different data types for sorting
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        if (columnKey === 'tow_date') { // Date sorting
            valA = new Date(valA);
            valB = new Date(valB);
        }
        // Add more type handling if needed (e.g., numbers)

        if (valA < valB) return appState.sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return appState.sortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    // Re-render the table with sorted data
    // Pass the current filter name, which should be stored in appState.lastVehicleTab or appState.currentTab
    renderVehicleTable(appState.vehiclesData, appState.lastVehicleTab || appState.currentTab);
}

/**
 * View details for a specific vehicle
 */
function viewVehicleDetails(callNumber) {
    // Find vehicle data
    const vehicle = appState.vehiclesData.find(v => 
        v.towbook_call_number === callNumber || v.call_number === callNumber
    );
    
    if (!vehicle) {
        console.error('Vehicle not found:', callNumber);
        return;
    }
    
    // Get the modal element
    const modal = document.getElementById('vehicleDetailsModal');
    if (!modal) {
        console.error('Vehicle details modal not found');
        return;
    }
    
    // Populate modal content
    // This is just a basic implementation - expand as needed for your actual data structure
    modal.querySelector('.modal-title').textContent = `Vehicle Details: ${callNumber}`;
    
    // Format vehicle info
    const vehicleInfo = `${vehicle.make || ''} ${vehicle.model || ''} ${vehicle.vehicle_year || ''}`.trim();
    const towDate = vehicle.tow_date ? new Date(vehicle.tow_date).toLocaleDateString() : 'N/A';
    
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h5>${vehicleInfo}</h5>
                <p><strong>License:</strong> ${vehicle.plate || 'N/A'} (${vehicle.state || 'N/A'})</p>
                <p><strong>VIN:</strong> ${vehicle.vin || 'N/A'}</p>
                <p><strong>Color:</strong> ${vehicle.color || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="status-label ${getStatusClass(vehicle.status)}">${vehicle.status}</span></p>
                <p><strong>Tow Date:</strong> ${towDate}</p>
                <p><strong>Jurisdiction:</strong> ${vehicle.jurisdiction || 'N/A'}</p>
                <p><strong>Location From:</strong> ${vehicle.location || 'N/A'}</p>
                <p><strong>Requested By:</strong> ${vehicle.requestor || 'N/A'}</p>
                <p><strong>Officer Name:</strong> ${vehicle.officer_name || 'N/A'}</p>
                <p><strong>Case Number:</strong> ${vehicle.case_number || 'N/A'}</p>
            </div>
            <div class="col-md-6">
                <h5>Owner Information</h5>
                <p><strong>Name:</strong> ${vehicle.owner_name || 'N/A'}</p>
                <p><strong>Address:</strong> ${vehicle.owner_address || 'N/A'}</p>
                <p><strong>Phone:</strong> ${vehicle.owner_phone || 'N/A'}</p>
                <p><strong>Email:</strong> ${vehicle.owner_email || 'N/A'}</p>
                <hr>
                <h5>Lienholder Information</h5>
                <p><strong>Name:</strong> ${vehicle.lienholder_name || 'N/A'}</p>
                <p><strong>Address:</strong> ${vehicle.lienholder_address || 'N/A'}</p>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-12">
                <h5>Form Generation History & Actions</h5>
                ${renderFormHistory(vehicle)}
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-12">
                <h5>Notes</h5>
                <p>${vehicle.notes || 'No notes available'}</p>
            </div>
        </div>
    `;
    // Store the original status in a data attribute for comparison later
    const statusSelect = modal.querySelector('#details-status');
    if (statusSelect) {
        statusSelect.setAttribute('data-original-status', vehicle.status);
    }

    // Show the modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Get CSS class for a vehicle status
 */
function getStatusClass(status) {
    switch (status) {
        case 'New': return 'status-new';
        case 'TOP Generated': return 'status-top-generated';
        case 'Ready for Auction': return 'status-ready-for-auction';
        case 'Ready for Scrap': return 'status-ready-for-scrap';
        case 'Released': return 'status-released';
        case 'Auctioned': return 'status-auctioned';
        case 'Scrapped': return 'status-scrapped';
        case 'Transferred': return 'status-transferred';
        default: return '';
    }
}

/**
 * Edit a vehicle
 */
function editVehicle(callNumber) {
    // Implement edit functionality
    console.log('Edit vehicle:', callNumber);
    // This would typically show the edit modal and populate it with data
}

/**
 * Show add vehicle modal
 */
function showAddVehicleModal() {
    const modal = document.getElementById('addVehicleModal');
    if (!modal) {
        console.error('Add vehicle modal not found');
        return;
    }

    // Reset the form
    const form = document.getElementById('addVehicleForm');
    if (form) {
        form.reset();
        // Set default date to today
        const todayDate = new Date().toISOString().split('T')[0];
        document.getElementById('add-tow_date').value = todayDate;
    }

    // Setup save button event listener
    const saveButton = document.getElementById('saveNewVehicleButton');
    if (saveButton) {
        // Remove any existing event listeners
        const newSaveButton = saveButton.cloneNode(true);
        saveButton.parentNode.replaceChild(newSaveButton, saveButton);
        newSaveButton.onclick = saveNewVehicle;
    }

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Save new vehicle from the add vehicle modal
 */
async function saveNewVehicle() {
    showLoading('Adding vehicle...');
    
    try {
        const form = document.getElementById('addVehicleForm');
        if (!form) {
            throw new Error('Add vehicle form not found');
        }

        // Collect form data
        const formData = new FormData(form);
        const vehicleData = {};
        
        // Convert FormData to regular object
        for (let [key, value] of formData.entries()) {
            // Only include non-empty values
            if (value && value.trim() !== '') {
                vehicleData[key] = value.trim();
            }
        }

        // Validate required fields
        if (!vehicleData.towbook_call_number) {
            throw new Error('Call number is required');
        }

        // Send the data to the API
        const response = await authenticatedFetch('/api/vehicles/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(vehicleData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to add vehicle: ${response.status}`);
        }

        const result = await response.json();
        
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addVehicleModal'));
        if (modal) {
            modal.hide();
        }

        // Show success message
        showToast('Vehicle added successfully!', 'success');

        // Refresh the vehicle list
        const currentTab = appState.currentTab || 'dashboard';
        if (currentTab.includes('vehicles') || currentTab === 'dashboard') {
            // Force refresh the current vehicles view
            appState.vehiclesData = []; // Clear cache
            if (currentTab === 'dashboard') {
                loadTab('dashboard', true);
            } else {
                const statusFilter = currentTab.replace('vehicles-', '') || 'active';
                loadVehicles(statusFilter, true);
            }
        }

    } catch (error) {
        console.error('Error adding vehicle:', error);
        showToast('Error adding vehicle: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Load notifications data
 */
function loadNotifications(forceRefresh = false) {
    console.log(`loadNotifications called, forceRefresh: ${forceRefresh}`);
    showLoading('Loading notifications...');

    // Basic cache check
    if (appState.notificationsData.length > 0 && !forceRefresh) {
        renderNotifications(appState.notificationsData);
        hideLoading();
        return;
    }

    fetch('/api/notifications') // Assuming this endpoint returns all notifications
        .then(response => {
            if (!response.ok) throw new Error(`API error: ${response.status}`);
            return response.json();
        })
        .then(data => {
            appState.notificationsData = data;
            renderNotifications(data);
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
            document.getElementById('dynamic-content-area').innerHTML = 
                `<div class="alert alert-danger">Failed to load notifications: ${error.message}</div>`;
        })
        .finally(() => hideLoading());
}

function renderNotifications(notifications) {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    let contentHtml = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h1 class="h2">Notifications</h1>
            <button class="btn btn-sm btn-outline-primary" id="clearAllNotifications">Clear All Read</button>
        </div>`;

    if (notifications.length === 0) {
        contentHtml += '<p>No notifications.</p>';
    } else {
        contentHtml += notifications.map(notification => `
            <div class="notification-item ${notification.is_read ? 'read' : 'unread'} ${notification.level || 'info'}" data-id="${notification.id}">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${notification.title}</h5>
                    <small>${new Date(notification.timestamp).toLocaleString()}</small>
                </div>
                <p class="mb-1">${notification.message}</p>
                <small>Related Vehicle ID: ${notification.vehicle_id || 'N/A'}</small>
                <button class="btn btn-sm btn-outline-secondary mark-as-read" data-id="${notification.id}" ${notification.is_read ? 'disabled' : ''}>Mark as Read</button>
            </div>
        `).join('');
    }
    dynamicContentArea.innerHTML = contentHtml;

    // Add event listeners for "Mark as Read" and "Clear All"
    document.querySelectorAll('.mark-as-read').forEach(button => {
        button.addEventListener('click', () => markNotificationAsRead(button.dataset.id));
    });
    const clearAllButton = document.getElementById('clearAllNotifications');
    if(clearAllButton) {
        clearAllButton.addEventListener('click', clearAllReadNotifications);
    }
}

/**
 * Dismiss a notification
 */
function dismissNotification(notificationId) {
    // Implement dismissal logic - this would typically update the notification status in the database
    console.log('Dismiss notification:', notificationId);
    
    // For now, just remove from the UI
    const notificationElement = document.querySelector(`.notification-item[data-id="${notificationId}"]`);
    if (notificationElement) {
        notificationElement.remove();
        
        // Also remove from state
        appState.notificationsData = appState.notificationsData.filter(n => n.id != notificationId);
        
        // Check if there are still notifications
        if (appState.notificationsData.length === 0) {
            document.getElementById('dynamic-content-area').innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-check-circle me-2"></i> No pending notifications.
                </div>
            `;
        }
        
        // Update notification badge
        const badge = document.getElementById('notification-count');
        if (badge) {
            if (appState.notificationsData.length > 0) {
                badge.textContent = appState.notificationsData.length;
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
        }
    }
}

/**
 * Load contacts data
 */
function loadContacts(forceRefresh = false) {
    console.log(`loadContacts called, forceRefresh: ${forceRefresh}`);
    showLoading('Loading contacts...');

    if (appState.contactsData.length > 0 && !forceRefresh) {
        renderContacts(appState.contactsData);
        hideLoading();
        return;
    }

    fetch('/api/contacts')
        .then(response => {
            if (!response.ok) throw new Error(`API error: ${response.status}`);
            return response.json();
        })
        .then(data => {
            appState.contactsData = data;
            renderContacts(data);
        })
        .catch(error => {
            console.error('Error loading contacts:', error);
            document.getElementById('dynamic-content-area').innerHTML = 
                `<div class="alert alert-danger">Failed to load contacts: ${error.message}</div>`;
        })
        .finally(() => hideLoading());
}

function renderContacts(contacts) {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    let contentHtml = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h1 class="h2">Jurisdiction Contacts</h1>
            <button class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#addContactModal">Add New Contact</button>
        </div>`;

    if (contacts.length === 0) {
        contentHtml += '<p>No contacts found. Add one to get started.</p>';
    } else {
        contentHtml += '<div class="contacts-list">';
        contentHtml += contacts.map(contact => `
            <div class="contact-card" data-id="${contact.id}">
                <h5>${contact.name} (${contact.jurisdiction_name})</h5>
                <p><strong>Email:</strong> ${contact.email || 'N/A'}</p>
                <p><strong>Phone:</strong> ${contact.phone || 'N/A'}</p>
                <p><strong>Address:</strong> ${contact.address || 'N/A'}</p>
                <p><strong>Notes:</strong> ${contact.notes || 'N/A'}</p>
                <div class="action-links">
                    <a href="#" class="edit-contact" data-id="${contact.id}" title="Edit Contact"><i class="fas fa-edit"></i></a>
                    <a href="#" class="delete-contact" data-id="${contact.id}" title="Delete Contact"><i class="fas fa-trash"></i></a>
                </div>
            </div>
        `).join('');
        contentHtml += '</div>';
    }
    dynamicContentArea.innerHTML = contentHtml;

    // Add event listeners for edit/delete (implementation needed in modals.js or here)
    document.querySelectorAll('.edit-contact').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            openEditContactModal(button.dataset.id);
        });
    });
    document.querySelectorAll('.delete-contact').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            deleteContact(button.dataset.id);
        });
    });
}

// Placeholder for deleteContact function
function deleteContact(contactId) {
    if (!confirm('Are you sure you want to delete this contact?')) return;
    
    fetch(`/api/contacts/${contactId}`, { method: 'DELETE' })
        .then(response => {
            if (!response.ok) throw new Error('Failed to delete contact');
            return response.json();
        })
        .then(data => {
            showToast(data.message || 'Contact deleted successfully', 'success');
            loadContacts(true); // Refresh contacts list
        })
        .catch(error => {
            console.error('Error deleting contact:', error);
            showToast(error.message || 'Error deleting contact', 'error');
        });
}

/**
 * Load reports data
 */
function loadReports() {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    dynamicContentArea.innerHTML = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h1 class="h2">Reports</h1>
        </div>
        <p>Report generation functionality is under development.</p>
        <!-- Placeholder for report options and display area -->
        <div id="report-options">
            <!-- Report type selection, date ranges, etc. -->
        </div>
        <div id="report-display-area">
            <!-- Charts and tables will be rendered here -->
        </div>
    `;
    hideLoading(); // Called by loadTab
}

/**
 * Load statistics data
 */
function loadStatistics() {
    console.log("loadStatistics called");
    showLoading('Loading statistics...');

    fetch('/api/statistics')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Statistics API request failed: ${response.status} ${response.statusText}`);
            }
            return response.json().catch(jsonError => {
                console.error('Failed to parse JSON for statistics:', jsonError);
                return response.text().then(text => {
                    console.error('Response text for failed statistics JSON:', text);
                    throw new Error('Invalid JSON response from statistics API. See console for response text.');
                });
            });
        })
        .then(statsData => {
            console.log("Statistics data fetched, calling renderStatisticsPage");
            renderStatisticsPage(statsData); // Call the new function
        })
        .catch(error => {
            console.error('Error in loadStatistics:', error);
            const dynamicContentArea = document.getElementById('dynamic-content-area');
            if (dynamicContentArea) {
                dynamicContentArea.innerHTML = `
                  <div class="alert alert-danger">
                      Failed to load statistics: ${error.message}. Check console for details.
                  </div>`;
            }
        })
        .finally(() => {
            console.log("loadStatistics finally block: calling hideLoading()");
            hideLoading();
        });
}

/**
 * Render the statistics page with various charts
 * @param {object} statisticsData - The data fetched from /api/statistics
 */
function renderStatisticsPage(statisticsData) {
    console.log('renderStatisticsPage called with data:', statisticsData);
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    if (!dynamicContentArea) {
        console.error('renderStatisticsPage: Dynamic content area not found!');
        return;
    }

    let statsHtml = `
        <div class="container-fluid pt-3">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                <h1 class="h2">Impound Statistics</h1>
            </div>

            <div class="row">
                <!-- Status Distribution Card -->
                <div class="col-lg-6 col-md-12 mb-4">
                    <div class="card h-100">
                        <div class="card-header">Vehicle Status Distribution</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <canvas id="statusDistChartStatsPage" style="display: none;"></canvas>
                            <p id="statusDistChartStatsPageMessage" class="text-center m-0"></p>
                        </div>
                    </div>
                </div>

                <!-- Average Processing Time Card -->
                <div class="col-lg-6 col-md-12 mb-4">
                    <div class="card h-100">
                        <div class="card-header">Average Processing Times (Days)</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <canvas id="avgProcTimeChartStatsPage" style="display: none;"></canvas>
                            <p id="avgProcTimeChartStatsPageMessage" class="text-center m-0"></p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <!-- Jurisdiction Distribution Card -->
                <div class="col-lg-6 col-md-12 mb-4">
                    <div class="card h-100">
                        <div class="card-header">Vehicle Distribution by Jurisdiction</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <canvas id="jurisdictionDistChartStatsPage" style="display: none;"></canvas>
                            <p id="jurisdictionDistChartStatsPageMessage" class="text-center m-0"></p>
                        </div>
                    </div>
                </div>

                <!-- Placeholder for another chart, e.g., Vehicles Over Time -->
                <div class="col-lg-6 col-md-12 mb-4">
                    <div class="card h-100">
                        <div class="card-header">Vehicle Trends Over Time (Example)</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <!-- <canvas id="vehicleTrendsChartStatsPage"></canvas> -->
                            <p id="vehicleTrendsChartStatsPageMessage" class="text-center m-0">Vehicle trend data is currently unavailable.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    dynamicContentArea.innerHTML = statsHtml;
    console.log('renderStatisticsPage: Initial HTML structure rendered.');

    // Render Status Distribution Chart
    const statusCtx = document.getElementById('statusDistChartStatsPage');
    const statusMsg = document.getElementById('statusDistChartStatsPageMessage');
    try {
        if (statisticsData && statisticsData.status_distribution && Object.keys(statisticsData.status_distribution).length > 0) {
            if(statusCtx) statusCtx.style.display = 'block';
            if(statusMsg) statusMsg.textContent = '';
            new Chart(statusCtx, {
                type: 'pie',
                data: {
                    labels: Object.keys(statisticsData.status_distribution),
                    datasets: [{
                        label: 'Status Distribution',
                        data: Object.values(statisticsData.status_distribution),
                        backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6c757d', '#6f42c1', '#20c997'],
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } } }
            });
        } else {
            if(statusCtx) statusCtx.style.display = 'none';
            if(statusMsg) statusMsg.textContent = 'Status distribution data is currently unavailable.';
        }
    } catch (e) {
        console.error('Error rendering status distribution chart on stats page:', e);
        if(statusCtx) statusCtx.style.display = 'none';
        if(statusMsg) statusMsg.textContent = 'Error displaying status distribution chart.';
    }

    // Render Average Processing Time Chart
    const avgTimeCtx = document.getElementById('avgProcTimeChartStatsPage');
    const avgTimeMsg = document.getElementById('avgProcTimeChartStatsPageMessage');
    try {
        if (statisticsData && statisticsData.average_processing_times && Object.keys(statisticsData.average_processing_times).length > 0) {
            if(avgTimeCtx) avgTimeCtx.style.display = 'block';
            if(avgTimeMsg) avgTimeMsg.textContent = '';
            new Chart(avgTimeCtx, {
                type: 'bar',
                data: {
                    labels: Object.keys(statisticsData.average_processing_times),
                    datasets: [{
                        label: 'Avg. Days',
                        data: Object.values(statisticsData.average_processing_times).map(d => parseFloat(d) || 0),
                        backgroundColor: '#17a2b8',
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, title: { display: true, text: 'Days'} } }, plugins: { legend: { display: false } } }
            });
        } else {
            if(avgTimeCtx) avgTimeCtx.style.display = 'none';
            if(avgTimeMsg) avgTimeMsg.textContent = 'Average processing time data is currently unavailable.';
        }
    } catch (e) {
        console.error('Error rendering average processing time chart on stats page:', e);
        if(avgTimeCtx) avgTimeCtx.style.display = 'none';
        if(avgTimeMsg) avgTimeMsg.textContent = 'Error displaying average processing time chart.';
    }

    // Render Jurisdiction Distribution Chart
    const jurCtx = document.getElementById('jurisdictionDistChartStatsPage');
    const jurMsg = document.getElementById('jurisdictionDistChartStatsPageMessage');
    try {
        if (statisticsData && statisticsData.jurisdiction_distribution && Object.keys(statisticsData.jurisdiction_distribution).length > 0) {
            if(jurCtx) jurCtx.style.display = 'block';
            if(jurMsg) jurMsg.textContent = '';
            new Chart(jurCtx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(statisticsData.jurisdiction_distribution),
                    datasets: [{
                        label: 'Jurisdiction',
                        data: Object.values(statisticsData.jurisdiction_distribution),
                        backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6f42c1', '#20c997', '#fd7e14'],
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } } }
            });
        } else {
            if(jurCtx) jurCtx.style.display = 'none';
            if(jurMsg) jurMsg.textContent = 'Jurisdiction distribution data is currently unavailable.';
        }
    } catch (e) {
        console.error('Error rendering jurisdiction distribution chart on stats page:', e);
        if(jurCtx) jurCtx.style.display = 'none';
        if(jurMsg) jurMsg.textContent = 'Error displaying jurisdiction distribution chart.';
    }

    // Placeholder for future charts, e.g., vehicles_over_time
    // const trendsCtx = document.getElementById('vehicleTrendsChartStatsPage');
    // const trendsMsg = document.getElementById('vehicleTrendsChartStatsPageMessage');
    // if (statisticsData && statisticsData.vehicles_over_time) { ... }

    console.log('renderStatisticsPage completed all rendering tasks.');
}

function loadCompliance() {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    dynamicContentArea.innerHTML = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h1 class="h2">Compliance Check</h1>
        </div>
        <p>Compliance check functionality is under development.</p>
        <!-- Placeholder for compliance tools and reports -->
    `;
    hideLoading(); // Called by loadTab
}

function loadProfile() {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    // Fetch user profile data if needed, or use appState.currentUser
    const user = appState.currentUser || { username: 'Guest', email: 'N/A', role: 'N/A' }; 
    dynamicContentArea.innerHTML = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h1 class="h2">User Profile</h1>
        </div>
        <p><strong>Username:</strong> ${user.username}</p>
        <p><strong>Email:</strong> ${user.email}</p>
        <p><strong>Role:</strong> ${user.role}</p>
        <!-- Add more profile details and edit options here -->
    `;
    hideLoading();
}

function loadLogs() {
    showLoading('Loading system logs...');
    fetch('/api/logs') // Assuming an endpoint for logs
        .then(response => {
            if (!response.ok) throw new Error(`API error: ${response.status}`);
            return response.json();
        })
        .then(data => {
            renderLogs(data);
        })
        .catch(error => {
            console.error('Error loading logs:', error);
            document.getElementById('dynamic-content-area').innerHTML = 
                `<div class="alert alert-danger">Failed to load system logs: ${error.message}</div>`;
        })
        .finally(() => hideLoading());
}

function renderLogs(logs) {
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    let contentHtml = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h1 class="h2">System Logs</h1>
            <!-- Add filtering options here if needed -->
        </div>`;
    
    if (logs.length === 0) {
        contentHtml += '<p>No logs found.</p>';
    } else {
        contentHtml += `
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Level</th>
                        <th>Message</th>
                        <th>User</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
        `;
        contentHtml += logs.map(log => `
            <tr>
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td><span class="badge bg-${log.level === 'ERROR' ? 'danger' : log.level === 'WARNING' ? 'warning' : 'info'}">${log.level}</span></td>
                <td>${log.message}</td>
                <td>${log.user_id || 'System'}</td>
                <td>${log.details ? `<pre style="max-height: 100px; overflow: auto;">${JSON.stringify(log.details, null, 2)}</pre>` : 'N/A'}</td>
            </tr>
        `).join('');
        contentHtml += '</tbody></table>';
    }
    dynamicContentArea.innerHTML = contentHtml;
}

/**
 * Opens the modal to view vehicle details.
 * @param {string} callNumber - The towbook_call_number of the vehicle.
 */
async function openVehicleDetailsModal(callNumber) {
    showLoading('Loading vehicle details...');
    try {
        const response = await fetch(`/api/vehicles/${callNumber}`, { credentials: 'include' });
        if (!response.ok) {
            throw new Error(`Failed to fetch vehicle details: ${response.status}`);
               }
        const vehicle = await response.json();

        const modalElement = document.getElementById('vehicleDetailsModal');
        if (!modalElement) {
            console.error('Vehicle details modal element not found.');
            hideLoading();
            return;
        }

        // Populate modal content (example, adjust to your modal's structure)
        modalElement.querySelector('.modal-title').textContent = `Vehicle Details: ${vehicle.make || 'N/A'} ${vehicle.model || 'N/A'} (${vehicle.vin || 'N/A'})`;
        
        // Format vehicle info
        const vehicleInfo = `${vehicle.make || ''} ${vehicle.model || ''} ${vehicle.vehicle_year || ''}`.trim();
        const towDate = vehicle.tow_date ? new Date(vehicle.tow_date).toLocaleDateString() : 'N/A';
        
        const modalBody = modalElement.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h5>${vehicleInfo}</h5>
                    <p><strong>License:</strong> ${vehicle.plate || 'N/A'} (${vehicle.state || 'N/A'})</p>
                    <p><strong>VIN:</strong> ${vehicle.vin || 'N/A'}</p>
                    <p><strong>Color:</strong> ${vehicle.color || 'N/A'}</p>
                    <p><strong>Status:</strong> <span class="status-label ${getStatusClass(vehicle.status)}">${vehicle.status}</span></p>
                    <p><strong>Tow Date:</strong> ${towDate}</p>
                    <p><strong>Jurisdiction:</strong> ${vehicle.jurisdiction || 'N/A'}</p>
                    <p><strong>Location From:</strong> ${vehicle.location || 'N/A'}</p>
                    <p><strong>Requested By:</strong> ${vehicle.requestor || 'N/A'}</p>
                    <p><strong>Officer Name:</strong> ${vehicle.officer_name || 'N/A'}</p>
                    <p><strong>Case Number:</strong> ${vehicle.case_number || 'N/A'}</p>
                </div>
                <div class="col-md-6">
                    <h5>Owner Information</h5>
                    <p><strong>Name:</strong> ${vehicle.owner_name || 'N/A'}</p>
                    <p><strong>Address:</strong> ${vehicle.owner_address || 'N/A'}</p>
                    <p><strong>Phone:</strong> ${vehicle.owner_phone || 'N/A'}</p>
                    <p><strong>Email:</strong> ${vehicle.owner_email || 'N/A'}</p>
                    <hr>
                    <h5>Lienholder Information</h5>
                    <p><strong>Name:</strong> ${vehicle.lienholder_name || 'N/A'}</p>
                    <p><strong>Address:</strong> ${vehicle.lienholder_address || 'N/A'}</p>
                </div>
            </div>
            <hr>
            <div class="row">
                <div class="col-12">
                    <h5>Form Generation History & Actions</h5>
                    ${renderFormHistory(vehicle)}
                </div>
            </div>
            <hr>
            <div class="row">
                <div class="col-12">
                    <h5>Notes</h5>
                    <p>${vehicle.notes || 'No notes available'}</p>
                </div>
            </div>
        `;
        // Store the original status in a data attribute for comparison later
        const statusSelect = modal.querySelector('#details-status');
        if (statusSelect) {
            statusSelect.setAttribute('data-original-status', vehicle.status);
        }

        // Show the modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

    } catch (error) {
        console.error('Error opening vehicle details modal:', error);
        showToast('Error loading vehicle details. ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Opens the modal to edit vehicle details.
 * @param {string} callNumber - The towbook_call_number of the vehicle.
 */
async function openEditVehicleModal(callNumber) {
    showLoading('Loading vehicle data for editing...');
    try {
        const response = await fetch(`/api/vehicles/${callNumber}`, { credentials: 'include' });
        if (!response.ok) {
            throw new Error(`Failed to fetch vehicle data: ${response.status}`);
        }
        const vehicle = await response.json();

        const modalElement = document.getElementById('editVehicleModal');
        if (!modalElement) {
            console.error('Edit vehicle modal element not found.');
            hideLoading();
            return;
        }

        // Populate modal form (example, adjust to your modal's form fields)
        // This assumes your edit modal has form inputs with IDs like 'edit-vin', 'edit-make', etc.
        modalElement.querySelector('.modal-title').textContent = `Edit Vehicle: ${vehicle.make || 'N/A'} ${vehicle.model || 'N/A'}`;
        document.getElementById('edit-vehicle-id').value = vehicle.towbook_call_number; // Hidden field for call number
        document.getElementById('edit-vin').value = vehicle.vin || '';
        document.getElementById('edit-year').value = vehicle.year || '';
        document.getElementById('edit-make').value = vehicle.make || '';
        document.getElementById('edit-model').value = vehicle.model || '';
        document.getElementById('edit-color').value = vehicle.color || '';
        // Populate vehicle type dropdown
        document.getElementById('edit-vehicle_type').value = vehicle.vehicle_type || '4-door';
        document.getElementById('edit-plate').value = vehicle.plate || '';
        document.getElementById('edit-state').value = vehicle.state || '';
        document.getElementById('edit-tow_date').value = formatDateForInput(vehicle.tow_date);
        document.getElementById('edit-tow_time').value = vehicle.tow_time || '';
        document.getElementById('edit-status').value = vehicle.status || '';
        document.getElementById('edit-location').value = vehicle.location || '';
        document.getElementById('edit-requestor').value = vehicle.requestor || '';
        document.getElementById('edit-reason_for_tow').value = vehicle.reason_for_tow || '';
        document.getElementById('edit-complaint_number').value = vehicle.complaint_number || '';
        document.getElementById('edit-jurisdiction').value = vehicle.jurisdiction || '';
        document.getElementById('edit-officer_name').value = vehicle.officer_name || '';
        document.getElementById('edit-case_number').value = vehicle.case_number || '';
        
        document.getElementById('edit-owner_name').value = vehicle.owner_name || '';
        document.getElementById('edit-owner_address').value = vehicle.owner_address || '';
        document.getElementById('edit-owner_phone').value = vehicle.owner_phone || '';
        document.getElementById('edit-owner_email').value = vehicle.owner_email || '';

        document.getElementById('edit-lienholder_name').value = vehicle.lienholder_name || '';
        document.getElementById('edit-lienholder_address').value = vehicle.lienholder_address || '';
        
        document.getElementById('edit-notes').value = vehicle.notes || '';

        // Setup save button
        const saveButton = document.getElementById('saveVehicleChangesButton');
        // Clone and replace to remove old event listeners
        const newSaveButton = saveButton.cloneNode(true);
        saveButton.parentNode.replaceChild(newSaveButton, saveButton);
        newSaveButton.onclick = () => saveVehicleChanges(callNumber);

        const bsModal = new bootstrap.Modal(modalElement);
        bsModal.show();

    } catch (error) {
        console.error('Error opening edit vehicle modal:', error);
        showToast('Error loading vehicle data for editing. ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Saves changes made to a vehicle in the edit modal.
 * @param {string} callNumber - The towbook_call_number of the vehicle being edited.
 */
async function saveVehicleChanges(callNumber) {
    showLoading('Saving vehicle changes...');
    const editForm = document.getElementById('editVehicleForm'); // Assuming your form has this ID
    if (!editForm) {
        console.error('Edit vehicle form not found.');
        hideLoading();
        showToast('Error: Edit form not found.', 'error');
        return;
    }

    const formData = new FormData(editForm);
    const data = {};
    formData.forEach((value, key) => data[key] = value);

    // Remove the hidden vehicle_id from the data payload if it was included by FormData
    // The callNumber parameter is used for the URL
    if (data.hasOwnProperty('vehicle_id')) {
        delete data.vehicle_id;
    }

    try {
        const response = await authenticatedFetch(`/api/vehicle/edit/${callNumber}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        // Get response text first, then try to parse as JSON
        const responseText = await response.text();
        let result;
        try {
            result = JSON.parse(responseText);
        } catch (jsonError) {
            // If response is not JSON, log the actual response for debugging
            console.error('Non-JSON response received:', responseText);
            throw new Error(`Server returned non-JSON response. Response was: ${responseText.substring(0, 200)}...`);
        }

        if (!response.ok) {
            throw new Error(result.error || `Failed to save changes: ${response.status}`);
        }

        showToast(result.message || 'Vehicle updated successfully!', 'success');
        const editModalElement = document.getElementById('editVehicleModal');
        const bsModal = bootstrap.Modal.getInstance(editModalElement);
        if (bsModal) {
            bsModal.hide();
        }
        loadTab(appState.currentTab, true); // Refresh current tab to show changes

    } catch (error) {
        console.error('Error saving vehicle changes:', error);
        
        // The global authentication handler will deal with auth errors,
        // so we only need to handle other types of errors here
        if (!error.message.includes('Authentication required') && !error.message.includes('401')) {
            showToast('Error saving changes: ' + error.message, 'error');
        }
    } finally {
        hideLoading();
    }
}

/**
 * Delete a vehicle from the system with confirmation
 * @param {string} callNumber - The towbook_call_number of the vehicle to delete
 */
function deleteVehicle(callNumber) {
    if (!confirm(`Are you sure you want to delete vehicle ${callNumber}? This action cannot be undone.`)) {
        return;
    }
    
    showLoading('Deleting vehicle...');
    
    fetch(`/api/vehicles/${callNumber}`, { 
        method: 'DELETE',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Failed to delete vehicle: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        showToast(data.message || 'Vehicle deleted successfully', 'success');
        loadTab(appState.currentTab, true); // Refresh current tab to remove deleted vehicle
    })
    .catch(error => {
        console.error('Error deleting vehicle:', error);
        if (!error.message.includes('Authentication required') && !error.message.includes('401')) {
            showToast('Error deleting vehicle: ' + error.message, 'error');
        }
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Calls the API to generate a document (TOP or Release Notice) for a vehicle.
 * @param {string} callNumber - The towbook_call_number of the vehicle.
 * @param {string} formTypeEndpoint - The API endpoint suffix (e.g., 'generate-top').
 * @param {string} formName - The user-friendly name of the form (e.g., 'TOP').
 */
async function generateDocumentApiCall(callNumber, formTypeEndpoint, formName) {
    showLoading(`Generating ${formName} form...`);
    try {
        const response = await fetch(`/api/${formTypeEndpoint}/${callNumber}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Add any other necessary headers, like CSRF token if used
            },
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || `Failed to generate ${formName}: ${response.status}`);
        }

        showToast(`${formName} generated successfully: ${result.pdf_filename || 'No filename returned'}`, 'success');
        
        // Open the PDF in a new tab: use pdf_url if provided, else construct URL from pdf_filename
        if (result.pdf_url) {
            window.open(result.pdf_url, '_blank');
        } else if (result.pdf_filename) {
            const pdfUrl = `/static/generated_pdfs/${result.pdf_filename}`;
            window.open(pdfUrl, '_blank');
        }

        loadTab(appState.currentTab, true); // Refresh to reflect potential status changes

    } catch (error) {
        console.error(`Error generating ${formName} for ${callNumber}:`, error);
        showToast(`Error generating ${formName}: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Date formatting utilities
/**
 * Format a date for display in the table (MM/DD/YYYY format)
 * @param {string} dateStr - Date string in various formats
 * @returns {string} - Formatted date string or 'N/A'
 */
function formatDateForDisplay(dateStr) {
    if (!dateStr || dateStr === 'N/A' || dateStr === '') {
        return 'N/A';
    }
    
    try {
        // Handle YYYY-MM-DD format specifically to avoid timezone issues
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            const [year, month, day] = dateStr.split('-');
            // Create date object using local timezone by specifying components
            const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
            
            // Check if date is valid
            if (isNaN(date.getTime())) {
                return dateStr; // Return original if can't parse
            }
            
            // Format as MM/DD/YYYY for display
            return date.toLocaleDateString('en-US', {
                month: '2-digit',
                day: '2-digit',
                year: 'numeric'
            });
        }
        
        // For other date formats, use the original parsing method
        const date = new Date(dateStr);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return dateStr; // Return original if can't parse
        }
        
        // Format as MM/DD/YYYY for display
        return date.toLocaleDateString('en-US', {
            month: '2-digit',
            day: '2-digit',
            year: 'numeric'
        });
    } catch (error) {
        console.warn('Date formatting error:', error, 'for date:', dateStr);
        return dateStr; // Return original string if error
    }
}

/**
 * Format a date for HTML date input (YYYY-MM-DD format)
 * @param {string} dateStr - Date string in various formats
 * @returns {string} - Date in YYYY-MM-DD format or empty string
 */
function formatDateForInput(dateStr) {
    if (!dateStr || dateStr === 'N/A' || dateStr === '') {
        return '';
    }
    
    try {
        // Handle YYYY-MM-DD format (already correct)
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return dateStr;
        }
        
        // Parse other formats and convert to YYYY-MM-DD
        const date = new Date(dateStr);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return ''; // Return empty if can't parse
        }
        
        // Format as YYYY-MM-DD for input
        return date.toISOString().split('T')[0];
    } catch (error) {
        console.warn('Date input formatting error:', error, 'for date:', dateStr);
        return ''; // Return empty string if error
    }
}

/**
 * Update vehicle status from the details modal
 */
async function updateVehicleStatus(callNumber) {
    const statusSelect = document.getElementById('details-status');
    if (!statusSelect) {
        showToast('Status dropdown not found', 'error');
        return;
    }

    const newStatus = statusSelect.value;
    const originalStatus = statusSelect.getAttribute('data-original-status') || statusSelect.options[statusSelect.selectedIndex].defaultSelected;

    if (!newStatus) {
        showToast('Please select a valid status', 'error');
        return;
    }

    try {
        showLoading('Updating vehicle status...');

        const response = await authenticatedFetch(`/api/vehicles/${callNumber}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                status: newStatus
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to update status: ${response.status}`);
        }

        showToast('Vehicle status updated successfully!', 'success');

        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('vehicleDetailsModal'));
        if (modal) {
            modal.hide();
        }

        // Refresh the current view
        const currentTab = appState.currentTab || 'dashboard';
        if (currentTab.includes('vehicles') || currentTab === 'dashboard') {
            // Force refresh the current vehicles view
            appState.vehiclesData = []; // Clear cache
            if (currentTab === 'dashboard') {
                loadTab('dashboard', true);
            } else {
                const statusFilter = currentTab.replace('vehicles-', '') || 'active';
                loadVehicles(statusFilter, true);
            }
        }

    } catch (error) {
        console.error('Error updating vehicle status:', error);
        showToast('Error updating vehicle status: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Convert frontend tab names to API status filter names
 */
function convertTabNameToStatusFilter(tabName) {
    // Convert underscored tab names to space-separated status names
    const conversions = {
        'TOP_Generated': 'TOP Generated',
        'Ready_for_Auction': 'Ready for Auction',
        'Ready_for_Scrap': 'Ready for Scrap'
    };
    
    return conversions[tabName] || tabName;
}

/**
 * Render form generation history and regeneration options for a vehicle
 * @param {object} vehicle - The vehicle object
 * @returns {string} - HTML string for form history section
 */
function renderFormHistory(vehicle) {
    const forms = [
        {
            name: 'TOP',
            endpoint: 'generate-top',
            generatedAt: vehicle.top_form_generated_at,
            generatedBy: vehicle.top_form_generated_by,
            condition: true, // TOP can always be generated/regenerated
            badgeClass: 'bg-primary'
        }
    ];

    let historyHtml = '<div class="form-history-container">';
    
    forms.forEach(form => {
        const isGenerated = form.generatedAt && form.generatedAt !== 'N/A';
        const canGenerate = form.condition;
        
        historyHtml += `
            <div class="card mb-2">
                <div class="card-body py-2">
                    <div class="row align-items-center">
                        <div class="col-md-3">
                            <span class="badge ${form.badgeClass} me-2">${form.name}</span>
                        </div>
                        <div class="col-md-5">
                            ${isGenerated ? 
                                `<small class="text-muted">
                                    Generated: ${formatDateTimeForDisplay(form.generatedAt)}<br>
                                    By: ${form.generatedBy || 'Unknown'}
                                </small>` : 
                                '<small class="text-muted">Not generated yet</small>'
                            }
                        </div>
                        <div class="col-md-4 text-end">
                            ${canGenerate ? 
                                `<button class="btn btn-sm ${isGenerated ? 'btn-outline-secondary' : 'btn-primary'} me-1" 
                                    onclick="generateDocumentApiCall('${vehicle.towbook_call_number}', '${form.endpoint}', '${form.name}')">
                                    <i class="fas ${isGenerated ? 'fa-redo' : 'fa-plus'}"></i> 
                                    ${isGenerated ? 'Regenerate' : 'Generate'}
                                </button>` : 
                                `<button class="btn btn-sm btn-secondary" disabled>
                                    <i class="fas fa-lock"></i> Not Available
                                </button>`
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    historyHtml += '</div>';
    return historyHtml;
}

/**
 * Format date and time for display in form history
 * @param {string} dateTimeStr - DateTime string
 * @returns {string} - Formatted date time string
 */
function formatDateTimeForDisplay(dateTimeStr) {
    if (!dateTimeStr || dateTimeStr === 'N/A') return 'N/A';
    
    try {
        const date = new Date(dateTimeStr);
        return date.toLocaleString();
    } catch (error) {
        return dateTimeStr;
    }
}
