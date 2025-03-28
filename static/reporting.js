/**
 * reporting.js - Enhanced Reporting Dashboard
 * 
 * This module provides reporting capabilities for lien processing and
 * vehicle management, including metrics, charts, and exports.
 */

// Initialize reporting
function initReporting() {
    // Add reporting button to header section
    addReportingButton();
    
    // Add export options to tables
    addExportOptions();
}

// Add reporting button to header
function addReportingButton() {
    const headerStats = document.querySelector('.header-stats');
    
    if (headerStats) {
        const reportingItem = document.createElement('div');
        reportingItem.className = 'stat-item';
        reportingItem.innerHTML = `
            <i class="fas fa-chart-bar stat-icon"></i>
            <button class="btn btn-neo-secondary btn-sm" id="reportingDashboardBtn">
                Reporting
            </button>
        `;
        
        headerStats.appendChild(reportingItem);
        
        // Add click event
        document.getElementById('reportingDashboardBtn').addEventListener('click', function() {
            showReportingDashboard();
        });
    }
}

// Show reporting dashboard
function showReportingDashboard() {
    // Create modal for reporting dashboard
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'reportingModal';
    modal.tabIndex = '-1';
    modal.setAttribute('role', 'dialog');
    
    modal.innerHTML = `
        <div class="modal-dialog modal-xl" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Reporting Dashboard</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="container-fluid">
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <div class="neo-card h-100">
                                    <div class="card-header">
                                        <div>Date Range</div>
                                    </div>
                                    <div class="card-body">
                                        <div class="row">
                                            <div class="col-md-5">
                                                <label class="form-label">Start Date</label>
                                                <input type="date" class="form-control" id="reportStartDate">
                                            </div>
                                            <div class="col-md-5">
                                                <label class="form-label">End Date</label>
                                                <input type="date" class="form-control" id="reportEndDate">
                                            </div>
                                            <div class="col-md-2 d-flex align-items-end">
                                                <button class="btn btn-neo-primary" id="updateReportBtn">
                                                    Update
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="neo-card h-100">
                                    <div class="card-header">
                                        <div>Export Options</div>
                                    </div>
                                    <div class="card-body">
                                        <div class="row">
                                            <div class="col-md-6">
                                                <label class="form-label">Report Type</label>
                                                <select class="form-select" id="reportType">
                                                    <option value="summary">Summary Report</option>
                                                    <option value="detailed">Detailed Report</option>
                                                    <option value="financial">Financial Report</option>
                                                </select>
                                            </div>
                                            <div class="col-md-6 d-flex align-items-end">
                                                <div class="btn-group w-100">
                                                    <button class="btn btn-neo-secondary" id="exportPdfBtn">
                                                        <i class="fas fa-file-pdf me-2"></i>PDF
                                                    </button>
                                                    <button class="btn btn-neo-secondary" id="exportCsvBtn">
                                                        <i class="fas fa-file-csv me-2"></i>CSV
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mb-4">
                            <div class="col-md-4">
                                <div class="neo-card h-100">
                                    <div class="card-header">
                                        <div>Vehicle Status</div>
                                    </div>
                                    <div class="card-body">
                                        <canvas id="statusChart" height="200"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="neo-card h-100">
                                    <div class="card-header">
                                        <div>Revenue</div>
                                    </div>
                                    <div class="card-body">
                                        <canvas id="revenueChart" height="200"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="neo-card h-100">
                                    <div class="card-header">
                                        <div>Processing Time</div>
                                    </div>
                                    <div class="card-body">
                                        <canvas id="timeChart" height="200"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6">
                                <div class="neo-card h-100">
                                    <div class="card-header">
                                        <div>Jurisdiction Distribution</div>
                                    </div>
                                    <div class="card-body">
                                        <canvas id="jurisdictionChart" height="250"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="neo-card h-100">
                                    <div class="card-header">
                                        <div>Key Metrics</div>
                                    </div>
                                    <div class="card-body">
                                        <div class="row g-3">
                                            <div class="col-md-6">
                                                <div class="metric-card">
                                                    <div class="metric-title">Avg. Processing Time</div>
                                                    <div class="metric-value" id="avgProcessingTime">-</div>
                                                </div>
                                            </div>
                                            <div class="col-md-6">
                                                <div class="metric-card">
                                                    <div class="metric-title">Total Vehicles</div>
                                                    <div class="metric-value" id="totalVehicles">-</div>
                                                </div>
                                            </div>
                                            <div class="col-md-6">
                                                <div class="metric-card">
                                                    <div class="metric-title">Revenue</div>
                                                    <div class="metric-value" id="totalRevenue">-</div>
                                                </div>
                                            </div>
                                            <div class="col-md-6">
                                                <div class="metric-card">
                                                    <div class="metric-title">Completion Rate</div>
                                                    <div class="metric-value" id="completionRate">-</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-neo-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body
    document.body.appendChild(modal);
    
    // Initialize Bootstrap modal
    const reportingModal = new bootstrap.Modal(modal);
    reportingModal.show();
    
    // Remove modal from DOM when hidden
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
    
    // Set default date range (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('reportStartDate').value = thirtyDaysAgo.toISOString().split('T')[0];
    document.getElementById('reportEndDate').value = today.toISOString().split('T')[0];
    
    // Load report data
    loadReportData();
    
    // Add event listeners
    document.getElementById('updateReportBtn').addEventListener('click', loadReportData);
    document.getElementById('exportPdfBtn').addEventListener('click', exportReportPdf);
    document.getElementById('exportCsvBtn').addEventListener('click', exportReportCsv);
}

// Load report data
function loadReportData() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    const reportType = document.getElementById('reportType').value;
    
    // Fetch report data
    fetch(`/api/reports?start_date=${startDate}&end_date=${endDate}&type=${reportType}`)
        .then(response => response.json())
        .then(data => {
            // Update charts
            updateStatusChart(data.status);
            updateRevenueChart(data.revenue);
            updateTimeChart(data.processingTime);
            updateJurisdictionChart(data.jurisdiction);
            
            // Update metrics
            document.getElementById('avgProcessingTime').textContent = data.metrics.avgProcessingTime;
            document.getElementById('totalVehicles').textContent = data.metrics.totalVehicles;
            document.getElementById('totalRevenue').textContent = data.metrics.totalRevenue;
            document.getElementById('completionRate').textContent = data.metrics.completionRate;
        })
        .catch(error => {
            console.error('Error loading report data:', error);
            showNotification('Error loading report data', 'error');
        });
}

// Update status chart
function updateStatusChart(data) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    
    if (window.statusChart) {
        window.statusChart.destroy();
    }
    
    window.statusChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: [
                    'rgba(134, 226, 119, 0.7)',  // success
                    'rgba(255, 189, 89, 0.7)',   // warning
                    'rgba(209, 107, 165, 0.7)',  // secondary
                    'rgba(255, 107, 107, 0.7)',  // danger
                    'rgba(184, 169, 198, 0.7)',  // text-secondary
                    'rgba(255, 141, 77, 0.7)',   // primary
                    'rgba(255, 210, 90, 0.7)'    // accent
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                position: 'right',
                labels: {
                    fontColor: '#f0e9e2'
                }
            }
        }
    });
}

// Update revenue chart
function updateRevenueChart(data) {
    const ctx = document.getElementById('revenueChart').getContext('2d');
    
    if (window.revenueChart) {
        window.revenueChart.destroy();
    }
    
    window.revenueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Revenue ($)',
                data: data.values,
                backgroundColor: 'rgba(255, 141, 77, 0.7)',
                borderColor: 'rgba(255, 141, 77, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true,
                        fontColor: '#f0e9e2'
                    },
                    gridLines: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }],
                xAxes: [{
                    ticks: {
                        fontColor: '#f0e9e2'
                    },
                    gridLines: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }]
            },
            legend: {
                labels: {
                    fontColor: '#f0e9e2'
                }
            }
        }
    });
}

// Update time chart
function updateTimeChart(data) {
    const ctx = document.getElementById('timeChart').getContext('2d');
    
    if (window.timeChart) {
        window.timeChart.destroy();
    }
    
    window.timeChart = new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Average Days',
                data: data.values,
                backgroundColor: 'rgba(209, 107, 165, 0.7)',
                borderColor: 'rgba(209, 107, 165, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                xAxes: [{
                    ticks: {
                        beginAtZero: true,
                        fontColor: '#f0e9e2'
                    },
                    gridLines: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }],
                yAxes: [{
                    ticks: {
                        fontColor: '#f0e9e2'
                    },
                    gridLines: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }]
            },
            legend: {
                labels: {
                    fontColor: '#f0e9e2'
                }
            }
        }
    });
}

// Update jurisdiction chart
function updateJurisdictionChart(data) {
    const ctx = document.getElementById('jurisdictionChart').getContext('2d');
    
    if (window.jurisdictionChart) {
        window.jurisdictionChart.destroy();
    }
    
    window.jurisdictionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: [
                    'rgba(255, 141, 77, 0.7)',   // primary
                    'rgba(209, 107, 165, 0.7)',  // secondary
                    'rgba(255, 210, 90, 0.7)',   // accent
                    'rgba(134, 226, 119, 0.7)',  // success
                    'rgba(255, 189, 89, 0.7)',   // warning
                    'rgba(255, 107, 107, 0.7)',  // danger
                    'rgba(184, 169, 198, 0.7)'   // text-secondary
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                position: 'right',
                labels: {
                    fontColor: '#f0e9e2'
                }
            }
        }
    });
}

// Export report as PDF
function exportReportPdf() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    const reportType = document.getElementById('reportType').value;
    
    const url = `/api/reports/export/pdf?start_date=${startDate}&end_date=${endDate}&type=${reportType}`;
    window.open(url, '_blank');
}

// Export report as CSV
function exportReportCsv() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    const reportType = document.getElementById('reportType').value;
    
    const url = `/api/reports/export/csv?start_date=${startDate}&end_date=${endDate}&type=${reportType}`;
    window.open(url, '_blank');
}

// Add export options to tables
function addExportOptions() {
    const tableContainer = document.querySelector('.table-responsive');
    
    if (tableContainer) {
        const exportContainer = document.createElement('div');
        exportContainer.className = 'd-flex justify-content-end mb-3';
        exportContainer.innerHTML = `
            <div class="btn-group">
                <button class="btn btn-neo-secondary export-btn" data-format="csv">
                    <i class="fas fa-file-csv me-2"></i>Export CSV
                </button>
                <button class="btn btn-neo-secondary export-btn" data-format="pdf">
                    <i class="fas fa-file-pdf me-2"></i>Export PDF
                </button>
            </div>
        `;
        
        // Insert before table
        tableContainer.parentNode.insertBefore(exportContainer, tableContainer);
        
        // Add click events
        exportContainer.querySelectorAll('.export-btn').forEach(button => {
            button.addEventListener('click', function() {
                const format = this.getAttribute('data-format');
                exportTableData(format);
            });
        });
    }
}

// Export table data
function exportTableData(format) {
    const tab = new URLSearchParams(window.location.search).get('tab') || 'active';
    const sortColumn = currentSortColumn || '';
    const sortDirection = currentSortDirection || 'asc';
    
    const url = `/api/vehicles/export/${format}?tab=${tab}&sort=${sortColumn}&direction=${sortDirection}`;
    window.open(url, '_blank');
}

// CSS for reporting
const reportingStyles = `
.metric-card {
    background: var(--surface-light);
    border-radius: 10px;
    padding: 15px;
    text-align: center;
    height: 100%;
}

.metric-title {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-bottom: 10px;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--primary);
}
`;

// Add reporting styles to document
function addReportingStyles() {
    const styleEl = document.createElement('style');
    styleEl.textContent = reportingStyles;
    document.head.appendChild(styleEl);
}

// Load required libraries
function loadChartJs() {
    return new Promise((resolve, reject) => {
        if (window.Chart) {
            resolve();
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.min.js';
        script.integrity = 'sha512-d9xgZrVZpmmQlfonhQUvTR7lMPtO7NkZMkA0ABN3PHCbKA5nqylQ/yWlFAyY6hYgdF1Qh6nYiuADWwKB4C2WSw==';
        script.crossOrigin = 'anonymous';
        
        script.onload = resolve;
        script.onerror = reject;
        
        document.head.appendChild(script);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load Chart.js
    loadChartJs()
        .then(() => {
            addReportingStyles();
            initReporting();
        })
        .catch(error => {
            console.error('Error loading Chart.js:', error);
        });
});