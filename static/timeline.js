/**
 * timeline.js - Vehicle Timeline Visualization
 * 
 * This module provides a visual timeline of a vehicle's history
 * in the system, including all status changes, document generation,
 * and other important events.
 */

// Initialize timeline functionality
function initTimeline() {
    // Add timeline button to action buttons
    const actionCells = document.querySelectorAll('.action-cell');
    
    actionCells.forEach(cell => {
        // Check if timeline button already exists
        if (!cell.querySelector('.timeline-btn')) {
            const timelineBtn = document.createElement('button');
            timelineBtn.className = 'action-btn btn btn-neo-primary timeline-btn action-tooltip';
            timelineBtn.setAttribute('data-tooltip', 'View Timeline');
            timelineBtn.innerHTML = '<i class="fas fa-history"></i>';
            
            // Get call number from row
            const callNumber = cell.closest('tr').getAttribute('data-call-number');
            timelineBtn.setAttribute('data-call-number', callNumber);
            
            // Add click event
            timelineBtn.addEventListener('click', function() {
                showVehicleTimeline(callNumber);
            });
            
            // Insert after the first button
            const firstBtn = cell.querySelector('.action-btn');
            if (firstBtn) {
                firstBtn.parentNode.insertBefore(timelineBtn, firstBtn.nextSibling);
            } else {
                cell.appendChild(timelineBtn);
            }
        }
    });
}

// Show vehicle timeline modal
function showVehicleTimeline(callNumber) {
    // Get vehicle data and logs
    Promise.all([
        fetch(`/api/vehicles?call_number=${callNumber}`).then(response => response.json()),
        fetch(`/api/logs?vehicle_id=${callNumber}`).then(response => response.json())
    ]).then(([vehicles, logs]) => {
        const vehicle = vehicles[0] || {};
        
        // Create timeline modal
        const timelineModal = createTimelineModal(vehicle, logs);
        
        // Show modal
        document.body.appendChild(timelineModal);
        
        // Initialize Bootstrap modal
        const modal = new bootstrap.Modal(timelineModal);
        modal.show();
        
        // Remove modal from DOM when hidden
        timelineModal.addEventListener('hidden.bs.modal', function() {
            timelineModal.remove();
        });
    }).catch(error => {
        console.error('Error fetching timeline data:', error);
        showNotification('Error loading timeline data', 'error');
    });
}

// Create timeline modal
function createTimelineModal(vehicle, logs) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'timelineModal';
    modal.tabIndex = '-1';
    modal.setAttribute('role', 'dialog');
    
    // Format vehicle info
    const makeModel = `${vehicle.make || ''} ${vehicle.model || ''}`.trim();
    
    // Create timeline events from logs
    const timelineEvents = processLogsForTimeline(logs);
    
    modal.innerHTML = `
        <div class="modal-dialog modal-lg" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Vehicle Timeline</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="container-fluid">
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <p><strong>Call #:</strong> ${vehicle.towbook_call_number || 'N/A'}</p>
                                <p><strong>Make/Model:</strong> ${makeModel || 'N/A'}</p>
                                <p><strong>VIN:</strong> ${vehicle.vin || 'N/A'}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Tow Date:</strong> ${vehicle.tow_date || 'N/A'}</p>
                                <p><strong>Current Status:</strong> ${vehicle.status || 'N/A'}</p>
                                <p><strong>Plate:</strong> ${vehicle.plate || 'N/A'}</p>
                            </div>
                        </div>
                        <div class="timeline">
                            ${timelineEvents}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-neo-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    
    return modal;
}

// Process logs to create timeline events
function processLogsForTimeline(logs) {
    if (!logs || logs.length === 0) {
        return '<div class="text-center my-5">No history available for this vehicle</div>';
    }
    
    // Sort logs chronologically (oldest first)
    logs.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    let timelineHtml = '';
    
    logs.forEach(log => {
        const timestamp = new Date(log.timestamp);
        let eventTitle = '';
        let eventClass = '';
        
        // Determine event type and class
        switch (log.action_type) {
            case 'INSERT':
                eventTitle = 'Vehicle Added';
                eventClass = 'event-insert';
                break;
            case 'STATUS_CHANGE':
                const statusMatch = log.details.match(/Changed status to (.+)/);
                eventTitle = statusMatch ? `Status: ${statusMatch[1]}` : 'Status Changed';
                eventClass = 'event-status';
                break;
            case 'GENERATE_TOP':
                eventTitle = 'TOP Form Generated';
                eventClass = 'event-document';
                break;
            case 'RELEASE':
                eventTitle = 'Vehicle Released';
                eventClass = 'event-release';
                break;
            case 'UPDATE':
                eventTitle = 'Information Updated';
                eventClass = 'event-update';
                break;
            default:
                eventTitle = log.action_type;
                eventClass = 'event-other';
        }
        
        timelineHtml += `
            <div class="timeline-item">
                <div class="timeline-point ${eventClass}"></div>
                <div class="timeline-content">
                    <div class="timeline-date">${timestamp.toLocaleString()}</div>
                    <h4 class="timeline-title">${eventTitle}</h4>
                    <div class="timeline-body">${log.details || ''}</div>
                </div>
            </div>
        `;
    });
    
    return timelineHtml;
}

// CSS for timeline
const timelineStyles = `
.timeline {
    position: relative;
    padding: 20px 0;
    margin-left: 20px;
}

.timeline::before {
    content: '';
    position: absolute;
    top: 0;
    left: 20px;
    height: 100%;
    width: 4px;
    background: var(--surface-light);
}

.timeline-item {
    position: relative;
    margin-bottom: 30px;
    padding-left: 50px;
}

.timeline-point {
    position: absolute;
    left: 18px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--primary);
    transform: translateY(10px);
}

.timeline-point.event-insert { background: var(--accent); }
.timeline-point.event-status { background: var(--primary); }
.timeline-point.event-document { background: var(--warning); }
.timeline-point.event-release { background: var(--success); }
.timeline-point.event-update { background: var(--secondary); }

.timeline-content {
    background: var(--surface);
    border-radius: 10px;
    padding: 15px;
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
}

.timeline-date {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.timeline-title {
    font-size: 1.1rem;
    margin-bottom: 8px;
    color: var(--primary);
}

.timeline-body {
    color: var(--text);
}
`;

// Add timeline styles to document
function addTimelineStyles() {
    const styleEl = document.createElement('style');
    styleEl.textContent = timelineStyles;
    document.head.appendChild(styleEl);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    addTimelineStyles();
    initTimeline();
    
    // Re-init timeline on table update
    document.addEventListener('tableUpdated', function() {
        initTimeline();
    });
});