/**
 * Main.js - Core functionality for iTow Impound Manager
 * Handles tab switching, data loading, and basic UI interactions
 */

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
        case 'TR52_Ready':
        case 'TR208_Ready':
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
            loadStatistics();
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
function checkNotifications() {
    fetch('/api/pending-notifications')
        .then(response => response.json())
        .then(data => {
            const count = data.length;
            const badge = document.getElementById('notification-count');
            if (badge) {
                if (count > 0) {
                    badge.textContent = count;
                    badge.classList.remove('d-none');
                } else {
                    badge.classList.add('d-none');
                }
            }
        })
        .catch(error => console.error('Error fetching notifications:', error));
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
function renderDashboard(workflowCounts, pendingNotifications, statisticsData) {
    console.log('renderDashboard called with data:', { workflowCounts, pendingNotifications, statisticsData });
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
function loadVehicles(tabName, forceRefresh = false) {
    console.log(`loadVehicles: Called for tab '${tabName}', forceRefresh: ${forceRefresh}`); // Added log
    // Determine the actual status filter to send to the API
    // 'active' and 'completed' are categories, not direct statuses.
    // The backend /api/vehicles endpoint expects specific statuses or 'all' / 'active_or_pending' / 'completed_states'
    let apiStatusFilter = tabName;
    if (tabName === 'active') {
        apiStatusFilter = 'active_or_pending'; // Tells backend to get all non-completed
    } else if (tabName === 'completed') {
        apiStatusFilter = 'completed_states'; // Tells backend to get all completed
    }
    // For specific statuses like 'New', 'TOP_Generated', etc., tabName is the status.

    // Only reload if forceRefresh is true, or if the current vehicle tab is different from the new one.
    if (forceRefresh || appState.lastVehicleTab !== tabName || !appState.vehiclesData.length) {
        appState.lastVehicleTab = tabName; // Update the last loaded vehicle tab
        
        let endpoint = `/api/vehicles?status=${apiStatusFilter}`;
        if (appState.sortColumn) {
            endpoint += `&sort=${appState.sortColumn}&direction=${appState.sortDirection}`;
        }
        console.log(`loadVehicles: Fetching endpoint: ${endpoint}`); // Added log
        
        fetch(endpoint)
            .then(response => {
                console.log(`loadVehicles: Received response for ${endpoint}, status: ${response.status}`); // Added log
                if (!response.ok) {
                    // Try to get text for more context, especially for non-JSON errors
                    return response.text().then(text => {
                        console.error(`loadVehicles: HTTP error! Status: ${response.status}. Response text: ${text}`);
                        throw new Error(`HTTP error! Status: ${response.status}. Details: ${text}`);
                    });
                }
                return response.json().catch(jsonError => {
                    console.error(`loadVehicles: Failed to parse JSON for endpoint ${endpoint}:`, jsonError);
                    // It's hard to get response.text() here if .json() already consumed or failed.
                    // The browser might show the raw response in network tab if it wasn't valid JSON.
                    throw new Error(`Invalid JSON response from vehicles API for ${apiStatusFilter}. Check network tab for raw response.`);
                });
            })
            .then(data => {
                console.log(`loadVehicles: Data received successfully for tab '${tabName}'. Vehicle count: ${data ? data.length : 'null'}. Calling renderVehiclesTable.`); // Added log
                appState.vehiclesData = data;
                renderVehiclesTable(data, tabName);
            })
            .catch(error => {
                console.error(`loadVehicles: Error loading vehicles for tab '${tabName}':`, error); // Enhanced log
                const dynamicContentArea = document.getElementById('dynamic-content-area');
                if (dynamicContentArea) {
                    dynamicContentArea.innerHTML = `
                        <div class="alert alert-danger">
                            <h4>Error Loading Data for ${tabName}</h4>
                            <p>${error.message || 'Could not load vehicles data'}</p>
                            <p>Please check the browser console for more details or try again. If the problem persists, contact support.</p>
                            <button class="btn btn-primary" onclick="loadTab('${tabName}', true)">Try Again</button>
                        </div>
                    `;
                } else {
                    console.error("loadVehicles: dynamic-content-area not found to display error.");
                }
            })
            .finally(() => {
                console.log(`loadVehicles: Finally block for tab '${tabName}'. Calling hideLoading().`); // Added log
                hideLoading();
            });
    } else {
        console.log(`loadVehicles: Using cached data for tab '${tabName}'. Calling renderVehiclesTable.`); // Added log
        renderVehiclesTable(appState.vehiclesData, tabName);
        hideLoading(); // Ensure loading is hidden if using cache and render is synchronous
    }
}

/**
 * Render the vehicles table with the provided data
 */
function renderVehiclesTable(vehicles, tabName) {
    console.log(`renderVehiclesTable: Called for tab '${tabName}'. Number of vehicles: ${vehicles ? vehicles.length : 'null/undefined'}`); // Added log
    const dynamicContentArea = document.getElementById('dynamic-content-area');
    if (!dynamicContentArea) {
        console.error("renderVehiclesTable: CRITICAL - dynamic-content-area not found!");
        hideLoading(); // Attempt to hide loading if it was shown
        return;
    }

    try {
        if (!vehicles || vehicles.length === 0) {
            console.log(`renderVehiclesTable: No vehicles found for tab '${tabName}'.`); // Added log
            dynamicContentArea.innerHTML = `
                <div class="alert alert-info">
                    <h4>No Vehicles Found</h4>
                    <p>There are no vehicles with status "${tabName}".</p>
                    <button class="btn btn-primary" id="add-vehicle-btn">
                        <i class="fas fa-plus"></i> Add Vehicle
                    </button>
                </div>
            `;
            return;
        }
        
        // Build table HTML
        let content = `
            <div class="mb-3 d-flex justify-content-between align-items-center">
                <button class="btn btn-primary" id="add-vehicle-btn">
                    <i class="fas fa-plus"></i> Add Vehicle
                </button>
                <div class="input-group" style="width: 300px;">
                    <input type="text" class="form-control" id="vehicle-search" placeholder="Search vehicles...">
                    <button class="btn btn-outline-secondary" type="button" id="btn-vehicle-search">
                        <i class="fas fa-search"></i>
                    </button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-striped table-hover vehicle-table">
                    <thead>
                        <tr>
                            <th data-sort="towbook_call_number">Call #</th>
                            <th data-sort="tow_date">Tow Date</th>
                            <th data-sort="make">Vehicle</th>
                            <th data-sort="license_plate">License</th>
                            <th data-sort="status">Status</th>
                            <th data-sort="jurisdiction">Jurisdiction</th>
                            <th data-sort="last_updated">Last Updated</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        // Add rows for each vehicle
        vehicles.forEach((vehicle, index) => {
            // console.log(`renderVehiclesTable: Processing vehicle index ${index}, ID: ${vehicle.towbook_call_number || vehicle.call_number}`); // Optional: very verbose log for per-vehicle processing
            // Format the status for display
            let statusClass = '';
            let statusDisplay = vehicle.status;
            
            // Map status to CSS classes
            switch (vehicle.status) {
                case 'New':
                    statusClass = 'status-new';
                    break;
                case 'TOP Generated':
                    statusClass = 'status-top-generated';
                    break;
                case 'TR52 Ready':
                    statusClass = 'status-tr52-ready';
                    break;
                case 'TR208 Ready':
                    statusClass = 'status-tr208-ready';
                    break;
                case 'Ready for Auction':
                    statusClass = 'status-ready-for-auction';
                    break;
                case 'Ready for Scrap':
                    statusClass = 'status-ready-for-scrap';
                    break;
                case 'Released':
                    statusClass = 'status-released';
                    break;
                case 'Auctioned':
                    statusClass = 'status-auctioned';
                    break;
                case 'Scrapped':
                    statusClass = 'status-scrapped';
                    break;
                case 'Transferred':
                    statusClass = 'status-transferred';
                    break;
                default:
                    statusClass = '';
            }
            
            // Format dates
            const towDate = vehicle.tow_date ? new Date(vehicle.tow_date).toLocaleDateString() : 'N/A';
            const lastUpdated = vehicle.last_updated ? new Date(vehicle.last_updated).toLocaleDateString() : 'N/A';
            
            // Vehicle details
            const vehicleInfo = `${vehicle.make || ''} ${vehicle.model || ''} ${vehicle.vehicle_year || ''}`.trim() || 'N/A';
            
            content += `
                <tr data-call-number="${vehicle.towbook_call_number}">
                    <td>${vehicle.towbook_call_number || vehicle.call_number || 'N/A'}</td>
                    <td>${towDate}</td>
                    <td>${vehicleInfo}</td>
                    <td>${vehicle.license_plate || 'N/A'}</td>
                    <td><span class="status-label ${statusClass}">${statusDisplay}</span></td>
                    <td>${vehicle.jurisdiction || 'N/A'}</td>
                    <td>${lastUpdated}</td>
                    <td>
                        <div class="btn-group">
                            <button type="button" class="btn btn-sm btn-info view-vehicle" data-call="${vehicle.towbook_call_number}">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-primary edit-vehicle" data-call="${vehicle.towbook_call_number}">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-secondary dropdown-toggle" data-bs-toggle="dropdown">
                                <i class="fas fa-ellipsis-v"></i>
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item generate-top" href="#" data-call="${vehicle.towbook_call_number}">Generate TOP</a></li>
                                <li><a class="dropdown-item generate-tr52" href="#" data-call="${vehicle.towbook_call_number}">Generate TR52</a></li>
                                <li><a class="dropdown-item generate-tr208" href="#" data-call="${vehicle.towbook_call_number}">Generate TR208</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item release-vehicle" href="#" data-call="${vehicle.towbook_call_number}">Release Vehicle</a></li>
                                <li><a class="dropdown-item auction-vehicle" href="#" data-call="${vehicle.towbook_call_number}">Add to Auction</a></li>
                                <li><a class="dropdown-item scrap-vehicle" href="#" data-call="${vehicle.towbook_call_number}">Mark for Scrap</a></li>
                            </ul>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        content += `
                    </tbody>
                </table>
            </div>
        `;
        
        document.getElementById('dynamic-content-area').innerHTML = content;
        
        console.log(`renderVehiclesTable: Finished rendering table for tab '${tabName}'. Setting up event handlers.`); // Added log
        // Set up table sorting
        setupTableSorting();
        
        // Set up action button handlers
        document.querySelectorAll('.view-vehicle').forEach(button => {
            button.addEventListener('click', function() {
                const callNumber = this.getAttribute('data-call');
                viewVehicleDetails(callNumber);
            });
        });
        
        document.querySelectorAll('.edit-vehicle').forEach(button => {
            button.addEventListener('click', function() {
                const callNumber = this.getAttribute('data-call');
                editVehicle(callNumber);
            });
        });
        
        // Set up add vehicle button
        document.getElementById('add-vehicle-btn')?.addEventListener('click', function() {
            showAddVehicleModal();
        });
        
        // Set up search functionality
        document.getElementById('btn-vehicle-search')?.addEventListener('click', function() {
            const searchText = document.getElementById('vehicle-search').value.toLowerCase();
            filterVehiclesTable(searchText);
        });
        
        document.getElementById('vehicle-search')?.addEventListener('keyup', function(event) {
            if (event.key === 'Enter') {
                const searchText = this.value.toLowerCase();
                filterVehiclesTable(searchText);
            }
        });
    } catch (error) {
        console.error(`renderVehiclesTable: Error during rendering for tab '${tabName}':`, error);
        if (dynamicContentArea) {
            dynamicContentArea.innerHTML = `<div class="alert alert-danger">Error rendering vehicle table for ${tabName}: ${error.message}. Check console.</div>`;
        }
        // hideLoading() should be called by the caller's finally block (loadVehicles)
        // but if renderVehiclesTable is called directly from cache path, ensure it's handled.
    }
}

/**
 * Filter the vehicles table based on search text
 */
function filterVehiclesTable(searchText) {
    if (!searchText) {
        // Reset table to show all rows
        document.querySelectorAll('.vehicle-table tbody tr').forEach(row => {
            row.style.display = '';
        });
        return;
    }
    
    document.querySelectorAll('.vehicle-table tbody tr').forEach(row => {
        const rowText = row.textContent.toLowerCase();
        if (rowText.includes(searchText)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

/**
 * Set up table column sorting
 */
function setupTableSorting() {
    document.querySelectorAll('.vehicle-table th[data-sort]').forEach(header => {
        header.addEventListener('click', function() {
            const sortColumn = this.getAttribute('data-sort');
            let sortDirection = 'asc';
            
            // Toggle direction if already sorting by this column
            if (appState.sortColumn === sortColumn) {
                sortDirection = appState.sortDirection === 'asc' ? 'desc' : 'asc';
            }
            
            // Update state
            appState.sortColumn = sortColumn;
            appState.sortDirection = sortDirection;
            
            // Reload data with new sort
            loadVehicles(appState.currentTab, true);
        });
    });
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
                <p><strong>License:</strong> ${vehicle.license_plate || 'N/A'} (${vehicle.license_state || 'N/A'})</p>
                <p><strong>VIN:</strong> ${vehicle.vin || 'N/A'}</p>
                <p><strong>Color:</strong> ${vehicle.color || 'N/A'}</p>
                <p><strong>Status:</strong> <span class="status-label ${getStatusClass(vehicle.status)}">${vehicle.status}</span></p>
                <p><strong>Tow Date:</strong> ${towDate}</p>
                <p><strong>Jurisdiction:</strong> ${vehicle.jurisdiction || 'N/A'}</p>
                <p><strong>Location From:</strong> ${vehicle.location_from || 'N/A'}</p>
            </div>
            <div class="col-md-6">
                <h5>Owner Information</h5>
                <p><strong>Name:</strong> ${vehicle.owner_name || 'Unknown'}</p>
                <p><strong>Address:</strong> ${vehicle.owner_address || 'Unknown'}</p>
                <p><strong>Phone:</strong> ${vehicle.owner_phone || 'Unknown'}</p>
                <p><strong>Email:</strong> ${vehicle.owner_email || 'Unknown'}</p>
                <hr>
                <h5>Lienholder Information</h5>
                <p><strong>Name:</strong> ${vehicle.lienholder_name || 'None'}</p>
                <p><strong>Address:</strong> ${vehicle.lienholder_address || 'N/A'}</p>
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
        case 'TR52 Ready': return 'status-tr52-ready';
        case 'TR208 Ready': return 'status-tr208-ready';
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
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Load notifications data
 */
function loadNotifications(forceRefresh = false) {
    // Only reload if we don't have data or force refresh is true
    if (forceRefresh || !appState.notificationsData.length) {
        fetch('/api/pending-notifications')
            .then(response => response.json())
            .then(data => {
                appState.notificationsData = data;
                renderNotifications(data);
            })
            .catch(error => {
                console.error('Error loading notifications:', error);
                document.getElementById('dynamic-content-area').innerHTML = `
                    <div class="alert alert-danger">
                        Error loading notifications: ${error.message}
                    </div>
                `;
            })
            .finally(() => {
                hideLoading();
            });
    } else {
        // Use cached data
        renderNotifications(appState.notificationsData);
        hideLoading();
    }
}

/**
 * Render notifications list
 */
function renderNotifications(notifications) {
    if (!notifications || notifications.length === 0) {
        document.getElementById('dynamic-content-area').innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-check-circle me-2"></i> No pending notifications.
            </div>
        `;
        return;
    }
    
    let content = `
        <div class="notifications-container">
    `;
    
    notifications.forEach(notification => {
        const isUrgent = notification.due_date && new Date(notification.due_date) < new Date();
        const notificationClass = isUrgent ? 'notification-item urgent' : 'notification-item';
        
        content += `
            <div class="${notificationClass}" data-id="${notification.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <h5>${notification.type}: ${notification.make || ''} ${notification.model || ''}</h5>
                    <span class="badge ${isUrgent ? 'bg-danger' : 'bg-warning'}">
                        ${notification.due_date ? new Date(notification.due_date).toLocaleDateString() : 'No due date'}
                    </span>
                </div>
                <p>${notification.message}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <div class="action-links">
                        <a href="#" class="view-notification-vehicle" data-call="${notification.towbook_call_number}">
                            <i class="fas fa-eye"></i> View Vehicle
                        </a>
                        <a href="#" class="send-notification" data-id="${notification.id}">
                            <i class="fas fa-paper-plane"></i> Send Notification
                        </a>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary dismiss-notification" data-id="${notification.id}">
                        Dismiss
                    </button>
                </div>
            </div>
        `;
    });
    
    content += `
        </div>
    `;
    
    document.getElementById('dynamic-content-area').innerHTML = content;
    
    // Set up event handlers for notification actions
    document.querySelectorAll('.view-notification-vehicle').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const callNumber = this.getAttribute('data-call');
            viewVehicleDetails(callNumber);
        });
    });
    
    document.querySelectorAll('.send-notification').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const notificationId = this.getAttribute('data-id');
            showSendNotificationModal(notificationId);
        });
    });
    
    document.querySelectorAll('.dismiss-notification').forEach(button => {
        button.addEventListener('click', function() {
            const notificationId = this.getAttribute('data-id');
            dismissNotification(notificationId);
        });
    });
}

/**
 * Show send notification modal
 */
function showSendNotificationModal(notificationId) {
    // Implement this to show the send notification modal
    console.log('Show send notification modal for ID:', notificationId);
    
    // Get notification data
    const notification = appState.notificationsData.find(n => n.id == notificationId);
    if (!notification) {
        console.error('Notification not found:', notificationId);
        return;
    }
    
    const modal = document.getElementById('sendNotificationModal');
    if (!modal) {
        console.error('Send notification modal not found');
        return;
    }
    
    // Set modal content
    modal.querySelector('.modal-title').textContent = `Send ${notification.type} Notification`;
    
    // Show the modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
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
    // Only reload if we don't have data or force refresh is true
    if (forceRefresh || !appState.contactsData.length) {
        fetch('/api/contacts')
            .then(response => response.json())
            .then(data => {
                appState.contactsData = data;
                renderContacts(data);
            })
            .catch(error => {
                console.error('Error loading contacts:', error);
                document.getElementById('dynamic-content-area').innerHTML = `
                    <div class="alert alert-danger">
                        Error loading contacts: ${error.message}
                    </div>
                `;
            })
            .finally(() => {
                hideLoading();
            });
    } else {
        // Use cached data
        renderContacts(appState.contactsData);
        hideLoading();
    }
}

/**
 * Render contacts list
 */
function renderContacts(contacts) {
    let content = `
        <div class="mb-3">
            <button class="btn btn-primary" id="add-contact-btn">
                <i class="fas fa-plus"></i> Add Contact
            </button>
        </div>
    `;
    
    if (!contacts || contacts.length === 0) {
        content += `
            <div class="alert alert-info">
                No jurisdiction contacts found. Click the button above to add contacts.
            </div>
        `;
    } else {
        content += `<div class="contacts-list">`;
        
        contacts.forEach(contact => {
            content += `
                <div class="contact-card" data-id="${contact.id}">
                    <h5>${contact.jurisdiction}</h5>
                    <p><strong>Contact:</strong> ${contact.contact_name || 'N/A'}</p>
                    <p><strong>Phone:</strong> ${contact.phone_number || 'N/A'}</p>
                    <p><strong>Email:</strong> ${contact.email_address || 'N/A'}</p>
                    <p><strong>Fax:</strong> ${contact.fax_number || 'N/A'}</p>
                    <div class="mt-2">
                        <button class="btn btn-sm btn-primary edit-contact" data-id="${contact.id}">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger delete-contact" data-id="${contact.id}">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            `;
        });
        
        content += `</div>`;
    }
    
    document.getElementById('dynamic-content-area').innerHTML = content;
    
    // Set up event handlers
    document.getElementById('add-contact-btn')?.addEventListener('click', function() {
        showAddContactModal();
    });
    
    document.querySelectorAll('.edit-contact').forEach(button => {
        button.addEventListener('click', function() {
            const contactId = this.getAttribute('data-id');
            editContact(contactId);
        });
    });
    
    document.querySelectorAll('.delete-contact').forEach(button => {
        button.addEventListener('click', function() {
            const contactId = this.getAttribute('data-id');
            deleteContact(contactId);
        });
    });
}

/**
 * Show add contact modal
 */
function showAddContactModal() {
    const modal = document.getElementById('addContactModal');
    if (!modal) {
        console.error('Add contact modal not found');
        return;
    }
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Edit a contact
 */
function editContact(contactId) {
    // Implement edit contact functionality
    console.log('Edit contact:', contactId);
}

/**
 * Delete a contact
 */
function deleteContact(contactId) {
    // Implement delete contact functionality
    console.log('Delete contact:', contactId);
}

/**
 * Load reports data
 */
function loadReports() {
    // Implement reports loading functionality
    document.getElementById('dynamic-content-area').innerHTML = `
        <div class="alert alert-info">
            Reports functionality is under development. Please check back soon.
        </div>
    `;
    hideLoading();
}

/**
 * Load statistics data
 */
function loadStatistics() {
    // Fetch statistics data
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            renderStatistics(data);
        })
        .catch(error => {
            console.error('Error loading statistics:', error);
            document.getElementById('dynamic-content-area').innerHTML = `
                <div class="alert alert-danger">
                    Error loading statistics: ${error.message}
                </div>
            `;
        })
        .finally(() => {
            hideLoading();
        });
}

/**
 * Render statistics
 */
function renderStatistics(data) {
    // Implement statistics rendering
    document.getElementById('dynamic-content-area').innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-header">
                        <h5>Vehicle Statistics</h5>
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Total Vehicles
                                <span class="badge bg-primary rounded-pill">${data.totalVehicles || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Active Vehicles
                                <span class="badge bg-info rounded-pill">${data.activeVehicles || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Released Vehicles
                                <span class="badge bg-secondary rounded-pill">${data.releasedVehicles || 0}</span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Avg. Processing Days
                                <span class="badge bg-dark rounded-pill">${data.averageProcessingTimeDays || 'N/A'}</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-header">
                        <h5>Jurisdiction Distribution</h5>
                    </div>
                    <div class="card-body" style="height: 300px;">
                        <canvas id="jurisdictionChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Create jurisdiction chart if Chart.js is loaded
    if (window.Chart && data.vehiclesByJurisdiction) {
        const ctx = document.getElementById('jurisdictionChart');
        if (ctx) {
            const labels = Object.keys(data.vehiclesByJurisdiction);
            const values = Object.values(data.vehiclesByJurisdiction);
            
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: [
                            '#007bff', '#17a2b8', '#28a745', '#ffc107', 
                            '#dc3545', '#6c757d', '#20c997', '#6610f2'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
    }
}

/**
 * Load compliance check data
 */
function loadCompliance() {
    // Implement compliance check functionality
    document.getElementById('dynamic-content-area').innerHTML = `
        <div class="alert alert-info">
            Compliance check functionality is under development. Please check back soon.
        </div>
    `;
    hideLoading();
}
