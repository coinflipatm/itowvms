/**
 * workflow.js - Automated Workflow Management
 * 
 * This module provides automated workflow suggestions and notifications
 * based on vehicle status and time thresholds.
 */

// Workflow steps and requirements
const workflowSteps = {
    'New': {
        nextStep: 'TOP Sent',
        action: 'Generate TOP Form',
        triggerDays: 2,
        description: 'Vehicle needs TOP form sent'
    },
    'TOP Sent': {
        nextStep: 'Ready for Disposition',
        action: 'Review for Disposition',
        triggerDays: {
            'Yes': 30, // 30 days if owner is known
            'No': 10   // 10 days if owner is unknown
        },
        description: 'Vehicle ready for disposition decision'
    },
    'Ready for Disposition': {
        nextStep: 'Decision Pending',
        action: 'Make Disposition Decision',
        triggerDays: 5,
        description: 'Decision needed on vehicle disposition'
    },
    'Decision Pending': {
        nextStep: ['Ready for Auction', 'Ready for Scrap', 'Released'],
        action: 'Finalize Disposition',
        triggerDays: 3,
        description: 'Finalize disposition decision'
    },
    'Ready for Auction': {
        nextStep: 'Auctioned',
        action: 'Process Auction',
        triggerDays: 7,
        description: 'Vehicle ready for auction processing'
    },
    'Ready for Scrap': {
        nextStep: 'Scrapped',
        action: 'Process Scrapping',
        triggerDays: 7,
        description: 'Vehicle ready for scrap processing'
    }
};

// Initialize workflow management
function initWorkflowManagement() {
    // Add status aging indicators to vehicle rows
    addStatusAgingIndicators();
    
    // Add workflow suggestions
    addWorkflowSuggestions();
    
    // Add workflow dashboard if admin
    if (isAdmin) {
        addWorkflowDashboard();
    }
}

// Add status aging indicators to vehicle rows
function addStatusAgingIndicators() {
    const vehicleRows = document.querySelectorAll('tr.vehicle-row');
    
    vehicleRows.forEach(row => {
        const status = row.getAttribute('data-status');
        const callNumber = row.getAttribute('data-call-number');
        
        // Get vehicle data
        fetch(`/api/vehicles?call_number=${callNumber}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    const vehicle = data[0];
                    
                    // Calculate days in current status
                    const lastUpdated = new Date(vehicle.last_updated);
                    const today = new Date();
                    const daysDiff = Math.floor((today - lastUpdated) / (1000 * 60 * 60 * 24));
                    
                    // Get threshold for current status
                    let threshold = workflowSteps[status]?.triggerDays || null;
                    
                    // Handle owner-dependent thresholds
                    if (typeof threshold === 'object' && vehicle.owner_known) {
                        threshold = threshold[vehicle.owner_known];
                    }
                    
                    // Apply aging indicator
                    if (threshold) {
                        if (daysDiff >= threshold * 1.5) {
                            row.classList.add('status-age-critical');
                        } else if (daysDiff >= threshold) {
                            row.classList.add('status-age-warning');
                        } else {
                            row.classList.add('status-age-normal');
                        }
                        
                        // Add days count to status cell
                        const statusCell = row.querySelector('td:nth-child(8)');
                        const daysIndicator = document.createElement('div');
                        daysIndicator.className = 'days-indicator';
                        daysIndicator.textContent = `${daysDiff} days`;
                        statusCell.appendChild(daysIndicator);
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching vehicle data:', error);
            });
    });
}

// Add workflow suggestions to vehicle rows
function addWorkflowSuggestions() {
    const vehicleRows = document.querySelectorAll('tr.vehicle-row');
    
    vehicleRows.forEach(row => {
        const status = row.getAttribute('data-status');
        const callNumber = row.getAttribute('data-call-number');
        
        if (workflowSteps[status]) {
            // Get vehicle data
            fetch(`/api/vehicles?call_number=${callNumber}`)
                .then(response => response.json())
                .then(data => {
                    if (data && data.length > 0) {
                        const vehicle = data[0];
                        
                        // Calculate days in current status
                        const lastUpdated = new Date(vehicle.last_updated);
                        const today = new Date();
                        const daysDiff = Math.floor((today - lastUpdated) / (1000 * 60 * 60 * 24));
                        
                        // Get threshold for current status
                        let threshold = workflowSteps[status].triggerDays || null;
                        
                        // Handle owner-dependent thresholds
                        if (typeof threshold === 'object' && vehicle.owner_known) {
                            threshold = threshold[vehicle.owner_known];
                        }
                        
                        // Add suggestion if threshold is exceeded
                        if (threshold && daysDiff >= threshold) {
                            const actionCell = row.querySelector('td:last-child');
                            
                            // Create suggestion button
                            const suggestionBtn = document.createElement('button');
                            suggestionBtn.className = 'action-btn btn btn-neo-warning suggestion-btn action-tooltip';
                            suggestionBtn.setAttribute('data-tooltip', workflowSteps[status].action);
                            suggestionBtn.innerHTML = '<i class="fas fa-tasks"></i>';
                            
                            // Add click event
                            suggestionBtn.addEventListener('click', function() {
                                handleWorkflowAction(callNumber, status, workflowSteps[status]);
                            });
                            
                            // Add to action cell
                            actionCell.appendChild(suggestionBtn);
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching vehicle data:', error);
                });
        }
    });
}

// Handle workflow action
function handleWorkflowAction(callNumber, currentStatus, workflowStep) {
    // Create modal for workflow action
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'workflowModal';
    modal.tabIndex = '-1';
    modal.setAttribute('role', 'dialog');
    
    let actionContent = '';
    
    // Generate appropriate content based on workflow step
    switch (currentStatus) {
        case 'New':
            actionContent = `
                <p>Generate TOP Form for vehicle ${callNumber}?</p>
                <button type="button" class="btn btn-neo-primary" id="generateTopBtn">
                    Generate TOP Form
                </button>
            `;
            break;
        case 'TOP Sent':
            actionContent = `
                <p>Mark vehicle ${callNumber} as Ready for Disposition?</p>
                <button type="button" class="btn btn-neo-primary" id="markReadyBtn">
                    Mark Ready for Disposition
                </button>
            `;
            break;
        case 'Ready for Disposition':
            actionContent = `
                <p>Make disposition decision for vehicle ${callNumber}:</p>
                <div class="btn-group mt-3">
                    <button type="button" class="btn btn-neo-accent" id="auctionBtn">
                        Auction
                    </button>
                    <button type="button" class="btn btn-neo-secondary" id="scrapBtn">
                        Scrap
                    </button>
                    <button type="button" class="btn btn-neo-primary" id="releaseBtn">
                        Release
                    </button>
                </div>
            `;
            break;
        case 'Ready for Auction':
        case 'Ready for Scrap':
            actionContent = `
                <p>Process ${currentStatus === 'Ready for Auction' ? 'auction' : 'scrapping'} for vehicle ${callNumber}?</p>
                <button type="button" class="btn btn-neo-primary" id="processBtn">
                    Process ${currentStatus === 'Ready for Auction' ? 'Auction' : 'Scrapping'}
                </button>
            `;
            break;
        default:
            actionContent = `
                <p>Update status for vehicle ${callNumber}?</p>
                <select class="form-select mb-3" id="statusSelect">
                    ${Object.keys(workflowSteps).map(status => 
                        `<option value="${status}" ${status === currentStatus ? 'selected' : ''}>${status}</option>`
                    ).join('')}
                </select>
                <button type="button" class="btn btn-neo-primary" id="updateStatusBtn">
                    Update Status
                </button>
            `;
    }
    
    modal.innerHTML = `
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Workflow Action: ${workflowStep.action}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    ${actionContent}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-neo-secondary" data-bs-dismiss="modal">Cancel</button>
                </div>
            </div>
        </div>
    `;
    
    // Append modal to body
    document.body.appendChild(modal);
    
    // Initialize Bootstrap modal
    const workflowModal = new bootstrap.Modal(modal);
    workflowModal.show();
    
    // Remove modal from DOM when hidden
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
    
    // Add event listeners based on action type
    modal.addEventListener('shown.bs.modal', function() {
        switch (currentStatus) {
            case 'New':
                document.getElementById('generateTopBtn').addEventListener('click', function() {
                    workflowModal.hide();
                    generateTop(callNumber);
                });
                break;
            case 'TOP Sent':
                document.getElementById('markReadyBtn').addEventListener('click', function() {
                    workflowModal.hide();
                    updateVehicleStatus(callNumber, 'Ready for Disposition');
                });
                break;
            case 'Ready for Disposition':
                document.getElementById('auctionBtn').addEventListener('click', function() {
                    workflowModal.hide();
                    updateVehicleStatus(callNumber, 'Ready for Auction');
                });
                document.getElementById('scrapBtn').addEventListener('click', function() {
                    workflowModal.hide();
                    updateVehicleStatus(callNumber, 'Ready for Scrap');
                });
                document.getElementById('releaseBtn').addEventListener('click', function() {
                    workflowModal.hide();
                    showReleaseModal(callNumber);
                });
                break;
            case 'Ready for Auction':
                document.getElementById('processBtn').addEventListener('click', function() {
                    workflowModal.hide();
                    updateVehicleStatus(callNumber, 'Auctioned', {
                        release_reason: 'Auctioned',
                        release_date: new Date().toISOString().split('T')[0],
                        archived: 1
                    });
                });
                break;
            case 'Ready for Scrap':
                document.getElementById('processBtn').addEventListener('click', function() {
                    workflowModal.hide();
                    updateVehicleStatus(callNumber, 'Scrapped', {
                        release_reason: 'Scrapped',
                        release_date: new Date().toISOString().split('T')[0],
                        archived: 1
                    });
                });
                break;
            default:
                document.getElementById('updateStatusBtn').addEventListener('click', function() {
                    const newStatus = document.getElementById('statusSelect').value;
                    workflowModal.hide();
                    updateVehicleStatus(callNumber, newStatus);
                });
        }
    });
}

// Update vehicle status from workflow
function updateVehicleStatus(callNumber, newStatus, additionalData = {}) {
    const data = {
        status: newStatus,
        ...additionalData
    };
    
    fetch(`/api/vehicles/${callNumber}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to update status');
        }
        return response.json();
    })
    .then(data => {
        showNotification(`Status updated to ${newStatus}`, 'success');
        
        // Reload vehicles table
        loadVehicles();
    })
    .catch(error => {
        console.error('Error updating status:', error);
        showNotification('Error updating status', 'error');
    });
}

// Add workflow dashboard to admin page
function addWorkflowDashboard() {
    const dashboardContainer = document.createElement('div');
    dashboardContainer.className = 'neo-card mb-4';
    dashboardContainer.innerHTML = `
        <div class="card-header">
            <div>
                <i class="fas fa-tasks card-header-icon"></i>
                Workflow Dashboard
            </div>
            <div>
                <button class="btn btn-sm btn-neo-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#workflowDashboardCollapse" aria-expanded="true">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>
        </div>
        <div class="collapse show" id="workflowDashboardCollapse">
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <div class="workflow-status-card">
                            <h3>Overdue Actions</h3>
                            <div id="overdueCount" class="workflow-count">0</div>
                            <button class="btn btn-neo-danger btn-sm view-all-btn" data-category="overdue">
                                View All
                            </button>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="workflow-status-card">
                            <h3>Due Today</h3>
                            <div id="dueTodayCount" class="workflow-count">0</div>
                            <button class="btn btn-neo-warning btn-sm view-all-btn" data-category="dueToday">
                                View All
                            </button>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="workflow-status-card">
                            <h3>Ready for Disposition</h3>
                            <div id="readyCount" class="workflow-count">0</div>
                            <button class="btn btn-neo-primary btn-sm view-all-btn" data-category="ready">
                                View All
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Insert before vehicles table
    const mainContainer = document.querySelector('.container');
    const tableContainer = document.querySelector('.table-responsive');
    mainContainer.insertBefore(dashboardContainer, tableContainer);
    
    // Add click handlers for view all buttons
    dashboardContainer.querySelectorAll('.view-all-btn').forEach(button => {
        button.addEventListener('click', function() {
            const category = this.getAttribute('data-category');
            showWorkflowCategoryModal(category);
        });
    });
    
    // Update workflow counts
    updateWorkflowCounts();
}

// Update workflow counts
function updateWorkflowCounts() {
    fetch('/api/workflow-counts')
        .then(response => response.json())
        .then(data => {
            document.getElementById('overdueCount').textContent = data.overdue;
            document.getElementById('dueTodayCount').textContent = data.dueToday;
            document.getElementById('readyCount').textContent = data.ready;
        })
        .catch(error => {
            console.error('Error fetching workflow counts:', error);
        });
}

// Show workflow category modal
function showWorkflowCategoryModal(category) {
    // Implement later...
}

// CSS for workflow management
const workflowStyles = `
.status-age-normal {
    border-left: 3px solid var(--success);
}

.status-age-warning {
    border-left: 3px solid var(--warning);
}

.status-age-critical {
    border-left: 3px solid var(--danger);
}

.days-indicator {
    font-size: 0.7rem;
    color: var(--text-secondary);
    display: block;
    margin-top: 5px;
}

.workflow-status-card {
    background: var(--surface-light);
    border-radius: 10px;
    padding: 15px;
    text-align: center;
    margin-bottom: 15px;
}

.workflow-status-card h3 {
    font-size: 1rem;
    margin-bottom: 10px;
    color: var(--text-secondary);
}

.workflow-count {
    font-size: 2rem;
    font-weight: bold;
    margin-bottom: 10px;
    color: var(--text);
}
`;

// Add workflow styles to document
function addWorkflowStyles() {
    const styleEl = document.createElement('style');
    styleEl.textContent = workflowStyles;
    document.head.appendChild(styleEl);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is admin
    const isAdmin = true; // Replace with actual admin check
    
    addWorkflowStyles();
    
    if (isAdmin) {
        initWorkflowManagement();
    } else {
        // Just add aging indicators for non-admin users
        addStatusAgingIndicators();
    }
    
    // Re-init on table update
    document.addEventListener('tableUpdated', function() {
        if (isAdmin) {
            initWorkflowManagement();
        } else {
            addStatusAgingIndicators();
        }
    });
});