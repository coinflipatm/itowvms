/**
 * automation.js - Automated Status Progression Management
 * 
 * This module provides a user interface for managing the automated
 * status progression scheduler and monitoring automated actions.
 */

// Initialize automation management
function initAutomation() {
    addAutomationDashboard();
    loadSchedulerStatus();
}

// Add automation dashboard to admin interface
function addAutomationDashboard() {
    const dashboardContainer = document.createElement('div');
    dashboardContainer.className = 'neo-card mb-4';
    dashboardContainer.id = 'automationDashboard';
    dashboardContainer.innerHTML = `
        <div class="card-header">
            <div>
                <i class="fas fa-robot card-header-icon"></i>
                Automated Status Progression
            </div>
            <div>
                <button class="btn btn-sm btn-neo-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#automationDashboardCollapse" aria-expanded="true">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>
        </div>
        <div class="collapse show" id="automationDashboardCollapse">
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="automation-status-card">
                            <h4>Scheduler Status</h4>
                            <div id="schedulerStatus" class="status-indicator">
                                <i class="fas fa-spinner fa-spin"></i> Checking...
                            </div>
                            <div id="schedulerJobs" class="mt-3">
                                <h5>Scheduled Tasks</h5>
                                <div id="jobsList" class="jobs-list">Loading...</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="automation-controls-card">
                            <h4>Manual Controls</h4>
                            <div class="btn-group-vertical w-100" role="group">
                                <button type="button" class="btn btn-neo-primary mb-2" id="triggerStatusCheck">
                                    <i class="fas fa-play me-2"></i>Run Status Check
                                </button>
                                <button type="button" class="btn btn-neo-accent mb-2" id="triggerAutoAdvance">
                                    <i class="fas fa-forward me-2"></i>Trigger Auto-Advance
                                </button>
                                <button type="button" class="btn btn-neo-secondary mb-2" id="refreshSchedulerStatus">
                                    <i class="fas fa-sync me-2"></i>Refresh Status
                                </button>
                                <button type="button" class="btn btn-neo-info" id="viewAutomationLogs">
                                    <i class="fas fa-history me-2"></i>View Automation Logs
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="row mt-4">
                    <div class="col-12">
                        <div class="automation-settings-card">
                            <h4>Automation Rules</h4>
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Status</th>
                                            <th>Trigger Threshold</th>
                                            <th>Auto-Advance Threshold</th>
                                            <th>Next Status</th>
                                            <th>Conditions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><span class="badge bg-info">New</span></td>
                                            <td>2 days</td>
                                            <td>3 days</td>
                                            <td>TOP Generated</td>
                                            <td>Always</td>
                                        </tr>
                                        <tr>
                                            <td><span class="badge bg-warning">TOP Generated</span></td>
                                            <td>20 days</td>
                                            <td>25 days</td>
                                            <td>Ready for Disposition</td>
                                            <td>After redemption period</td>
                                        </tr>
                                        <tr>
                                            <td><span class="badge bg-primary">Ready for Disposition</span></td>
                                            <td>5 days</td>
                                            <td>7 days</td>
                                            <td>Ready for Auction</td>
                                            <td>Auto-decision</td>
                                        </tr>
                                        <tr>
                                            <td><span class="badge bg-success">Ready for Auction</span></td>
                                            <td>7 days</td>
                                            <td>Manual only</td>
                                            <td>Auctioned</td>
                                            <td>Requires processing</td>
                                        </tr>
                                        <tr>
                                            <td><span class="badge bg-secondary">Ready for Scrap</span></td>
                                            <td>27 days from tow</td>
                                            <td>Manual only</td>
                                            <td>Scrapped</td>
                                            <td>Requires processing</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="automation-info">
                            <h5><i class="fas fa-info-circle me-2"></i>How Automated Status Progression Works</h5>
                            <ul class="list-unstyled">
                                <li><strong>Status Checks:</strong> Run every hour to update days counters and create notifications</li>
                                <li><strong>Auto-Advancement:</strong> Runs every 6 hours to automatically progress vehicles past time thresholds</li>
                                <li><strong>Notifications:</strong> Processed every 30 minutes to track overdue actions</li>
                                <li><strong>Safety:</strong> Only advances vehicles that clearly meet criteria - auction/scrap require manual processing</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Insert at the top of the main container, after workflow dashboard
    const mainContainer = document.querySelector('.container');
    const workflowDashboard = document.getElementById('workflowDashboardCollapse')?.closest('.neo-card');
    if (workflowDashboard) {
        workflowDashboard.parentNode.insertBefore(dashboardContainer, workflowDashboard.nextSibling);
    } else {
        const tableContainer = document.querySelector('.table-responsive');
        if (tableContainer) {
            mainContainer.insertBefore(dashboardContainer, tableContainer);
        }
    }
    
    // Add event listeners
    document.getElementById('triggerStatusCheck').addEventListener('click', triggerStatusCheck);
    document.getElementById('triggerAutoAdvance').addEventListener('click', triggerAutoAdvance);
    document.getElementById('refreshSchedulerStatus').addEventListener('click', loadSchedulerStatus);
    document.getElementById('viewAutomationLogs').addEventListener('click', showAutomationLogs);
}

// Load and display scheduler status
function loadSchedulerStatus() {
    fetch('/api/scheduler/status')
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById('schedulerStatus');
            const jobsElement = document.getElementById('jobsList');
            
            // Update status indicator
            if (data.running) {
                statusElement.innerHTML = '<i class="fas fa-check-circle text-success"></i> Running';
                statusElement.className = 'status-indicator text-success';
            } else {
                statusElement.innerHTML = '<i class="fas fa-times-circle text-danger"></i> Stopped';
                statusElement.className = 'status-indicator text-danger';
            }
            
            // Update jobs list
            if (data.jobs && data.jobs.length > 0) {
                const jobsHtml = data.jobs.map(job => {
                    const nextRun = job.next_run ? new Date(job.next_run).toLocaleString() : 'Not scheduled';
                    return `
                        <div class="job-item">
                            <div class="job-name">${job.name}</div>
                            <div class="job-next-run text-muted">Next: ${nextRun}</div>
                        </div>
                    `;
                }).join('');
                jobsElement.innerHTML = jobsHtml;
            } else {
                jobsElement.innerHTML = '<div class="text-muted">No scheduled jobs</div>';
            }
        })
        .catch(error => {
            console.error('Error loading scheduler status:', error);
            document.getElementById('schedulerStatus').innerHTML = '<i class="fas fa-exclamation-triangle text-warning"></i> Error loading status';
        });
}

// Manually trigger status check
function triggerStatusCheck() {
    const button = document.getElementById('triggerStatusCheck');
    const originalHtml = button.innerHTML;
    
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Running...';
    button.disabled = true;
    
    fetch('/api/scheduler/trigger', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Status progression check completed successfully', 'success');
        } else {
            showNotification('Status progression check completed with issues', 'warning');
        }
    })
    .catch(error => {
        console.error('Error triggering status check:', error);
        showNotification('Error triggering status check', 'error');
    })
    .finally(() => {
        button.innerHTML = originalHtml;
        button.disabled = false;
        // Refresh the vehicles view to show any updates
        setTimeout(() => {
            if (typeof loadVehicles === 'function') {
                loadVehicles(true);
            }
        }, 1000);
    });
}

// Manually trigger auto-advance
function triggerAutoAdvance() {
    const button = document.getElementById('triggerAutoAdvance');
    const originalHtml = button.innerHTML;
    
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    button.disabled = true;
    
    fetch('/api/scheduler/auto-advance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Automatic status advancement completed', 'success');
        } else {
            showNotification('Error in automatic status advancement', 'error');
        }
    })
    .catch(error => {
        console.error('Error triggering auto-advance:', error);
        showNotification('Error triggering auto-advance', 'error');
    })
    .finally(() => {
        button.innerHTML = originalHtml;
        button.disabled = false;
        // Refresh the vehicles view to show any updates
        setTimeout(() => {
            if (typeof loadVehicles === 'function') {
                loadVehicles(true);
            }
        }, 1000);
    });
}

// Show automation logs modal
function showAutomationLogs() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'automationLogsModal';
    modal.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Automation Activity Logs</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <label for="logFilter" class="form-label">Filter by action:</label>
                            <select class="form-select" id="logFilter" style="width: auto; display: inline-block;">
                                <option value="">All automated actions</option>
                                <option value="AUTO_STATUS">Auto Status Changes</option>
                                <option value="AUTO_ADVANCE">Auto Advancement</option>
                                <option value="NOTIFICATION">Notifications</option>
                                <option value="SYSTEM_CLEANUP">System Cleanup</option>
                            </select>
                        </div>
                        <button class="btn btn-neo-secondary btn-sm" id="refreshLogs">
                            <i class="fas fa-sync me-1"></i>Refresh
                        </button>
                    </div>
                    <div id="automationLogsContent">
                        <div class="text-center">
                            <i class="fas fa-spinner fa-spin"></i> Loading logs...
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-neo-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const automationModal = new bootstrap.Modal(modal);
    automationModal.show();
    
    // Load logs
    loadAutomationLogs();
    
    // Add event listeners
    document.getElementById('logFilter').addEventListener('change', loadAutomationLogs);
    document.getElementById('refreshLogs').addEventListener('click', loadAutomationLogs);
    
    // Remove modal when hidden
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
}

// Load automation logs
function loadAutomationLogs() {
    const filter = document.getElementById('logFilter')?.value || '';
    const content = document.getElementById('automationLogsContent');
    
    fetch(`/api/logs?filter=${filter}&limit=100`)
        .then(response => response.json())
        .then(logs => {
            if (logs.length === 0) {
                content.innerHTML = '<div class="text-center text-muted">No automation logs found</div>';
                return;
            }
            
            // Filter for automation-related logs
            const automationLogs = logs.filter(log => 
                log.action_type.includes('AUTO') || 
                log.action_type.includes('NOTIFICATION') ||
                log.action_type.includes('SYSTEM_CLEANUP')
            );
            
            if (automationLogs.length === 0) {
                content.innerHTML = '<div class="text-center text-muted">No automation logs found</div>';
                return;
            }
            
            const logsHtml = automationLogs.map(log => {
                const timestamp = new Date(log.timestamp).toLocaleString();
                let badgeClass = 'bg-info';
                
                if (log.action_type.includes('AUTO_ADVANCE')) badgeClass = 'bg-success';
                else if (log.action_type.includes('AUTO_STATUS')) badgeClass = 'bg-primary';
                else if (log.action_type.includes('NOTIFICATION')) badgeClass = 'bg-warning';
                else if (log.action_type.includes('SYSTEM_CLEANUP')) badgeClass = 'bg-secondary';
                
                return `
                    <div class="log-entry border-bottom py-2">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <span class="badge ${badgeClass} me-2">${log.action_type}</span>
                                <strong>${log.user_id}</strong>
                            </div>
                            <small class="text-muted">${timestamp}</small>
                        </div>
                        <div class="mt-1">${log.details}</div>
                    </div>
                `;
            }).join('');
            
            content.innerHTML = logsHtml;
        })
        .catch(error => {
            console.error('Error loading automation logs:', error);
            content.innerHTML = '<div class="text-center text-danger">Error loading logs</div>';
        });
}

// CSS for automation dashboard
const automationStyles = `
.automation-status-card,
.automation-controls-card,
.automation-settings-card {
    background: var(--surface-light);
    border-radius: 10px;
    padding: 15px;
    height: 100%;
}

.automation-info {
    background: var(--surface-light);
    border-radius: 10px;
    padding: 15px;
    border-left: 4px solid var(--accent);
}

.status-indicator {
    font-size: 1.1rem;
    font-weight: bold;
}

.jobs-list .job-item {
    background: var(--surface);
    border-radius: 5px;
    padding: 8px;
    margin-bottom: 5px;
}

.job-name {
    font-weight: 500;
}

.job-next-run {
    font-size: 0.85rem;
}

.log-entry:last-child {
    border-bottom: none !important;
}

#automationDashboard .table th {
    border-top: none;
    background: var(--surface);
}

#automationDashboard .badge {
    font-size: 0.8rem;
}
`;

// Add automation styles to document
function addAutomationStyles() {
    const styleEl = document.createElement('style');
    styleEl.textContent = automationStyles;
    document.head.appendChild(styleEl);
}

// Initialize automation when document is ready
document.addEventListener('DOMContentLoaded', function() {
    addAutomationStyles();
    
    // Initialize automation if on admin/vehicles page
    if (window.location.pathname.includes('admin') || document.querySelector('.table-responsive')) {
        // Delay initialization to ensure other components are loaded
        setTimeout(() => {
            if (typeof isAdmin !== 'undefined' && isAdmin) {
                initAutomation();
            }
        }, 1000);
    }
});

// Auto-refresh scheduler status every 5 minutes
setInterval(() => {
    if (document.getElementById('schedulerStatus')) {
        loadSchedulerStatus();
    }
}, 5 * 60 * 1000);
