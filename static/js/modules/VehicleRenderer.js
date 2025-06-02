/**
 * VehicleRenderer.js - Professional Vehicle UI Rendering Module
 * 
 * Handles all vehicle-related UI rendering with proper separation of concerns,
 * error handling, and maintainable code structure.
 */

class VehicleRenderer {
    constructor(vehicleManager) {
        this.vehicleManager = vehicleManager;
        this.currentView = 'table';
        this.tableConfig = {
            sortable: true,
            selectable: true,
            responsive: true
        };
        
        // Templates for different views
        this.templates = new VehicleTemplates();
        
        // Subscribe to vehicle manager events
        this.vehicleManager.subscribe(this.handleVehicleEvent.bind(this));
        
        // Bind methods
        this.renderVehicleTable = this.renderVehicleTable.bind(this);
        this.renderVehicleCard = this.renderVehicleCard.bind(this);
    }

    /**
     * Handle vehicle manager events
     * @param {string} event - Event type
     * @param {any} data - Event data
     */
    handleVehicleEvent(event, data) {
        switch (event) {
            case 'dataLoaded':
                this.renderVehicles(data.vehicles, data.filter);
                break;
            case 'vehicleUpdated':
                this.updateVehicleInView(data.vehicle);
                break;
            case 'vehicleAdded':
                this.addVehicleToView(data.vehicle);
                break;
            case 'vehicleDeleted':
                this.removeVehicleFromView(data.callNumber);
                break;
            case 'loading':
                this.showLoadingState(data.filter);
                break;
            case 'error':
                this.showErrorState(data.error);
                break;
            case 'searchResults':
                this.renderSearchResults(data.results, data.query);
                break;
        }
    }

    /**
     * Main method to render vehicles
     * @param {Array} vehicles - Vehicle data
     * @param {string} filter - Current filter
     */
    renderVehicles(vehicles, filter) {
        const container = this.getContentContainer();
        if (!container) {
            console.error('Content container not found');
            return;
        }

        try {
            // Clear loading state
            this.hideLoadingState();

            // Render header
            const header = this.renderHeader(filter, vehicles.length);
            container.innerHTML = '';
            container.appendChild(header);

            // Render vehicles based on current view
            switch (this.currentView) {
                case 'table':
                    container.appendChild(this.renderVehicleTable(vehicles));
                    break;
                case 'cards':
                    container.appendChild(this.renderVehicleCards(vehicles));
                    break;
                case 'compact':
                    container.appendChild(this.renderCompactView(vehicles));
                    break;
                default:
                    container.appendChild(this.renderVehicleTable(vehicles));
            }

            // Add action handlers
            this.attachEventHandlers(container);

        } catch (error) {
            console.error('Error rendering vehicles:', error);
            this.showErrorState('Failed to render vehicle list');
        }
    }

    /**
     * Render vehicle table view
     * @param {Array} vehicles - Vehicle data
     * @returns {HTMLElement} Table element
     */
    renderVehicleTable(vehicles) {
        const tableContainer = document.createElement('div');
        tableContainer.className = 'table-responsive';

        const table = document.createElement('table');
        table.className = 'table table-striped table-hover vehicle-table';
        table.setAttribute('data-view', 'table');

        // Table header
        const thead = this.createTableHeader();
        table.appendChild(thead);

        // Table body
        const tbody = this.createTableBody(vehicles);
        table.appendChild(tbody);

        tableContainer.appendChild(table);
        return tableContainer;
    }

    /**
     * Create table header with sorting capability
     * @returns {HTMLElement} Table header
     */
    createTableHeader() {
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        const columns = this.getTableColumns();
        
        columns.forEach(column => {
            const th = document.createElement('th');
            th.textContent = column.label;
            th.className = 'sortable';
            th.setAttribute('data-column', column.key);
            th.setAttribute('data-sortable', column.sortable ? 'true' : 'false');
            
            if (column.sortable) {
                th.style.cursor = 'pointer';
                th.setAttribute('title', `Sort by ${column.label}`);
                
                // Add sort indicator if this column is currently sorted
                const currentSort = this.vehicleManager.sortConfig;
                if (currentSort.column === column.key) {
                    th.classList.add(currentSort.direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
                }
            }

            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        return thead;
    }

    /**
     * Create table body with vehicle rows
     * @param {Array} vehicles - Vehicle data
     * @returns {HTMLElement} Table body
     */
    createTableBody(vehicles) {
        const tbody = document.createElement('tbody');

        if (vehicles.length === 0) {
            const emptyRow = this.createEmptyRow();
            tbody.appendChild(emptyRow);
            return tbody;
        }

        vehicles.forEach(vehicle => {
            const row = this.createVehicleRow(vehicle);
            tbody.appendChild(row);
        });

        return tbody;
    }

    /**
     * Create a single vehicle row
     * @param {Object} vehicle - Vehicle data
     * @returns {HTMLElement} Table row
     */
    createVehicleRow(vehicle) {
        const row = document.createElement('tr');
        row.setAttribute('data-vehicle-id', vehicle.towbook_call_number);
        row.className = 'vehicle-row';

        const columns = this.getTableColumns();
        
        columns.forEach(column => {
            const cell = document.createElement('td');
            cell.className = `vehicle-${column.key}`;
            
            const content = this.renderCellContent(vehicle, column);
            if (typeof content === 'string') {
                cell.innerHTML = content;
            } else {
                cell.appendChild(content);
            }
            
            row.appendChild(cell);
        });

        // Add row selection capability
        row.addEventListener('click', (e) => {
            if (!e.target.closest('.action-buttons')) {
                this.toggleRowSelection(row);
            }
        });

        return row;
    }

    /**
     * Render content for a table cell
     * @param {Object} vehicle - Vehicle data
     * @param {Object} column - Column configuration
     * @returns {string|HTMLElement} Cell content
     */
    renderCellContent(vehicle, column) {
        const value = vehicle[column.key];
        
        switch (column.type) {
            case 'text':
                return this.escapeHtml(value || 'N/A');
                
            case 'date':
                return this.formatDate(value);
                
            case 'status':
                return this.renderStatusBadge(value);
                
            case 'actions':
                return this.renderActionButtons(vehicle);
                
            case 'days':
                return this.calculateDaysInLot(vehicle.tow_date);
                
            case 'vehicle_info':
                return this.renderVehicleInfo(vehicle);
                
            default:
                return this.escapeHtml(value || 'N/A');
        }
    }

    /**
     * Render status badge
     * @param {string} status - Vehicle status
     * @returns {HTMLElement} Status badge
     */
    renderStatusBadge(status) {
        const badge = document.createElement('span');
        badge.className = `badge status-badge ${this.getStatusClass(status)}`;
        badge.textContent = status || 'Unknown';
        badge.setAttribute('title', `Status: ${status}`);
        return badge;
    }

    /**
     * Render action buttons for a vehicle
     * @param {Object} vehicle - Vehicle data
     * @returns {HTMLElement} Action buttons container
     */
    renderActionButtons(vehicle) {
        const container = document.createElement('div');
        container.className = 'action-buttons d-flex gap-1';

        const actions = this.getAvailableActions(vehicle);
        
        actions.forEach(action => {
            const button = this.createActionButton(action, vehicle);
            container.appendChild(button);
        });

        return container;
    }

    /**
     * Create an action button
     * @param {Object} action - Action configuration
     * @param {Object} vehicle - Vehicle data
     * @returns {HTMLElement} Button element
     */
    createActionButton(action, vehicle) {
        const button = document.createElement('button');
        button.className = `btn btn-sm ${action.class || 'btn-outline-secondary'}`;
        button.innerHTML = action.icon ? `<i class="${action.icon}"></i>` : action.label;
        button.setAttribute('title', action.tooltip || action.label);
        button.setAttribute('data-action', action.name);
        button.setAttribute('data-vehicle-id', vehicle.towbook_call_number);
        
        if (action.disabled && action.disabled(vehicle)) {
            button.disabled = true;
            button.classList.add('disabled');
        }

        return button;
    }

    /**
     * Render vehicle cards view
     * @param {Array} vehicles - Vehicle data
     * @returns {HTMLElement} Cards container
     */
    renderVehicleCards(vehicles) {
        const container = document.createElement('div');
        container.className = 'row vehicle-cards';

        if (vehicles.length === 0) {
            const emptyState = this.createEmptyState();
            container.appendChild(emptyState);
            return container;
        }

        vehicles.forEach(vehicle => {
            const cardCol = document.createElement('div');
            cardCol.className = 'col-lg-4 col-md-6 mb-4';
            
            const card = this.createVehicleCard(vehicle);
            cardCol.appendChild(card);
            container.appendChild(cardCol);
        });

        return container;
    }

    /**
     * Create a vehicle card
     * @param {Object} vehicle - Vehicle data
     * @returns {HTMLElement} Card element
     */
    createVehicleCard(vehicle) {
        const card = document.createElement('div');
        card.className = 'card vehicle-card h-100';
        card.setAttribute('data-vehicle-id', vehicle.towbook_call_number);

        const vehicleInfo = `${vehicle.year || ''} ${vehicle.make || ''} ${vehicle.model || ''}`.trim() || 'Unknown Vehicle';

        card.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">${this.escapeHtml(vehicleInfo)}</h6>
                ${this.renderStatusBadge(vehicle.status).outerHTML}
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-6">
                        <small class="text-muted">Call Number</small>
                        <div class="fw-bold">${this.escapeHtml(vehicle.towbook_call_number || 'N/A')}</div>
                    </div>
                    <div class="col-6">
                        <small class="text-muted">Tow Date</small>
                        <div>${this.formatDate(vehicle.tow_date)}</div>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-6">
                        <small class="text-muted">License</small>
                        <div>${this.escapeHtml(vehicle.plate || 'N/A')}</div>
                    </div>
                    <div class="col-6">
                        <small class="text-muted">Days in Lot</small>
                        <div class="text-primary fw-bold">${this.calculateDaysInLot(vehicle.tow_date)}</div>
                    </div>
                </div>
                ${vehicle.location ? `
                <div class="mt-2">
                    <small class="text-muted">Location</small>
                    <div class="text-truncate">${this.escapeHtml(vehicle.location)}</div>
                </div>
                ` : ''}
            </div>
            <div class="card-footer">
                ${this.renderActionButtons(vehicle).outerHTML}
            </div>
        `;

        return card;
    }

    /**
     * Render header section
     * @param {string} filter - Current filter
     * @param {number} count - Number of vehicles
     * @returns {HTMLElement} Header element
     */
    renderHeader(filter, count) {
        const header = document.createElement('div');
        header.className = 'vehicle-header d-flex justify-content-between align-items-center mb-4';

        const title = document.createElement('div');
        title.innerHTML = `
            <h4 class="mb-1">Vehicles - ${this.formatFilterName(filter)}</h4>
            <small class="text-muted">${count} vehicle${count !== 1 ? 's' : ''} found</small>
        `;

        const controls = document.createElement('div');
        controls.className = 'd-flex gap-2 align-items-center';
        controls.innerHTML = `
            <div class="btn-group" role="group" aria-label="View options">
                <button type="button" class="btn btn-outline-secondary btn-sm view-toggle ${this.currentView === 'table' ? 'active' : ''}" data-view="table">
                    <i class="fas fa-table"></i> Table
                </button>
                <button type="button" class="btn btn-outline-secondary btn-sm view-toggle ${this.currentView === 'cards' ? 'active' : ''}" data-view="cards">
                    <i class="fas fa-th-large"></i> Cards
                </button>
            </div>
            <button class="btn btn-primary btn-sm" id="addVehicleBtn">
                <i class="fas fa-plus"></i> Add Vehicle
            </button>
            <div class="dropdown">
                <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
                    <i class="fas fa-cog"></i>
                </button>
                <ul class="dropdown-menu">
                    <li><a class="dropdown-item" href="#" data-action="export">Export Data</a></li>
                    <li><a class="dropdown-item" href="#" data-action="refresh">Refresh</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="#" data-action="bulk-edit">Bulk Edit</a></li>
                </ul>
            </div>
        `;

        header.appendChild(title);
        header.appendChild(controls);

        return header;
    }

    /**
     * Attach event handlers to the container
     * @param {HTMLElement} container - Container element
     */
    attachEventHandlers(container) {
        // View toggle handlers
        container.querySelectorAll('.view-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.target.closest('button').getAttribute('data-view');
                this.changeView(view);
            });
        });

        // Sort handlers
        container.querySelectorAll('th[data-sortable="true"]').forEach(th => {
            th.addEventListener('click', (e) => {
                const column = e.target.getAttribute('data-column');
                this.handleSort(column);
            });
        });

        // Action button handlers
        container.addEventListener('click', (e) => {
            const actionBtn = e.target.closest('[data-action]');
            if (actionBtn) {
                e.preventDefault();
                const action = actionBtn.getAttribute('data-action');
                const vehicleId = actionBtn.getAttribute('data-vehicle-id');
                this.handleAction(action, vehicleId, actionBtn);
            }
        });

        // Add vehicle handler
        const addBtn = container.querySelector('#addVehicleBtn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.handleAddVehicle());
        }
    }

    /**
     * Handle sorting
     * @param {string} column - Column to sort by
     */
    handleSort(column) {
        const currentSort = this.vehicleManager.sortConfig;
        const direction = (currentSort.column === column && currentSort.direction === 'asc') ? 'desc' : 'asc';
        
        this.vehicleManager.sortVehicles(column, direction);
    }

    /**
     * Handle view changes
     * @param {string} view - New view type
     */
    changeView(view) {
        if (this.currentView !== view) {
            this.currentView = view;
            
            // Update active state
            document.querySelectorAll('.view-toggle').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-view') === view);
            });

            // Re-render with current data
            const vehicles = this.vehicleManager.getVehicles();
            this.renderVehicles(vehicles, this.vehicleManager.currentFilter);
        }
    }

    /**
     * Handle actions
     * @param {string} action - Action type
     * @param {string} vehicleId - Vehicle ID (if applicable)
     * @param {HTMLElement} button - Button element
     */
    async handleAction(action, vehicleId, button) {
        try {
            switch (action) {
                case 'view':
                    this.showVehicleDetails(vehicleId);
                    break;
                case 'edit':
                    this.showEditModal(vehicleId);
                    break;
                case 'delete':
                    await this.handleDelete(vehicleId);
                    break;
                case 'generate-form':
                    this.generateForm(vehicleId, button.getAttribute('data-form-type'));
                    break;
                case 'export':
                    this.exportData();
                    break;
                case 'refresh':
                    await this.vehicleManager.loadVehicles(this.vehicleManager.currentFilter, true);
                    break;
                default:
                    console.warn('Unknown action:', action);
            }
        } catch (error) {
            console.error('Error handling action:', error);
            this.showToast('Action failed. Please try again.', 'error');
        }
    }

    // Utility methods

    /**
     * Get table columns configuration
     * @returns {Array} Column definitions
     */
    getTableColumns() {
        return [
            { key: 'towbook_call_number', label: 'Call #', type: 'text', sortable: true },
            { key: 'complaint_number', label: 'Complaint #', type: 'text', sortable: true },
            { key: 'vehicle_info', label: 'Vehicle', type: 'vehicle_info', sortable: false },
            { key: 'plate', label: 'License', type: 'text', sortable: true },
            { key: 'tow_date', label: 'Tow Date', type: 'date', sortable: true },
            { key: 'status', label: 'Status', type: 'status', sortable: true },
            { key: 'days_in_lot', label: 'Days', type: 'days', sortable: false },
            { key: 'actions', label: 'Actions', type: 'actions', sortable: false }
        ];
    }

    /**
     * Get available actions for a vehicle
     * @param {Object} vehicle - Vehicle data
     * @returns {Array} Available actions
     */
    getAvailableActions(vehicle) {
        const baseActions = [
            {
                name: 'view',
                label: 'View',
                icon: 'fas fa-eye',
                class: 'btn-outline-primary',
                tooltip: 'View Details'
            },
            {
                name: 'edit',
                label: 'Edit',
                icon: 'fas fa-edit',
                class: 'btn-outline-secondary',
                tooltip: 'Edit Vehicle'
            }
        ];

        // Add conditional actions based on vehicle status
        if (vehicle.status !== 'Released' && vehicle.status !== 'Scrapped') {
            baseActions.push({
                name: 'delete',
                label: 'Delete',
                icon: 'fas fa-trash',
                class: 'btn-outline-danger',
                tooltip: 'Delete Vehicle',
                disabled: (v) => v.status === 'Auctioned'
            });
        }

        return baseActions;
    }

    /**
     * Format date for display
     * @param {string} dateStr - Date string
     * @returns {string} Formatted date
     */
    formatDate(dateStr) {
        if (!dateStr || dateStr === 'N/A') return 'N/A';
        
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } catch (error) {
            return 'Invalid Date';
        }
    }

    /**
     * Calculate days in lot
     * @param {string} towDate - Tow date string
     * @returns {string} Days in lot
     */
    calculateDaysInLot(towDate) {
        if (!towDate || towDate === 'N/A') return 'N/A';
        
        try {
            const tow = new Date(towDate);
            const now = new Date();
            const diffTime = Math.abs(now - tow);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            return diffDays.toString();
        } catch (error) {
            return 'N/A';
        }
    }

    /**
     * Get CSS class for status
     * @param {string} status - Vehicle status
     * @returns {string} CSS class
     */
    getStatusClass(status) {
        const statusClasses = {
            'New': 'bg-primary',
            'TOP Generated': 'bg-info',
            'Ready for Auction': 'bg-warning text-dark',
            'Ready for Scrap': 'bg-warning text-dark',
            'Released': 'bg-secondary',
            'Auctioned': 'bg-success',
            'Scrapped': 'bg-danger'
        };
        return statusClasses[status] || 'bg-secondary';
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, m => map[m]);
    }

    /**
     * Format filter name for display
     * @param {string} filter - Filter name
     * @returns {string} Formatted name
     */
    formatFilterName(filter) {
        return filter.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Show loading state
     * @param {string} filter - Current filter
     */
    showLoadingState(filter) {
        const container = this.getContentContainer();
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2 text-muted">Loading ${this.formatFilterName(filter)} vehicles...</p>
                </div>
            `;
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        // Loading state is cleared when content is rendered
    }

    /**
     * Show error state
     * @param {string} error - Error message
     */
    showErrorState(error) {
        const container = this.getContentContainer();
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <h5>Error Loading Vehicles</h5>
                    <p>${this.escapeHtml(error)}</p>
                    <button class="btn btn-outline-danger" onclick="location.reload()">
                        <i class="fas fa-refresh"></i> Reload Page
                    </button>
                </div>
            `;
        }
    }

    /**
     * Get main content container
     * @returns {HTMLElement|null} Container element
     */
    getContentContainer() {
        return document.getElementById('dynamic-content-area');
    }

    /**
     * Show toast notification
     * @param {string} message - Message to show
     * @param {string} type - Toast type
     */
    showToast(message, type = 'info') {
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            alert(message); // Fallback
        }
    }

    // Additional helper methods for actions
    showVehicleDetails(vehicleId) {
        // Implementation would show vehicle details modal
        console.log('Show vehicle details:', vehicleId);
    }

    showEditModal(vehicleId) {
        // Implementation would show edit modal
        console.log('Show edit modal:', vehicleId);
    }

    async handleDelete(vehicleId) {
        if (confirm('Are you sure you want to delete this vehicle?')) {
            await this.vehicleManager.deleteVehicle(vehicleId);
        }
    }

    generateForm(vehicleId, formType) {
        // Implementation would generate forms
        console.log('Generate form:', formType, 'for vehicle:', vehicleId);
    }

    exportData() {
        // Implementation would export current data
        console.log('Export data');
    }

    handleAddVehicle() {
        // Implementation would show add vehicle modal
        console.log('Add new vehicle');
    }

    // Create empty state elements
    createEmptyRow() {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = this.getTableColumns().length;
        cell.className = 'text-center text-muted py-4';
        cell.innerHTML = `
            <i class="fas fa-car fa-2x mb-2"></i>
            <p>No vehicles found matching the current criteria.</p>
        `;
        row.appendChild(cell);
        return row;
    }

    createEmptyState() {
        const div = document.createElement('div');
        div.className = 'col-12';
        div.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-car fa-3x mb-3"></i>
                <h5>No Vehicles Found</h5>
                <p>No vehicles match the current criteria.</p>
            </div>
        `;
        return div;
    }

    renderVehicleInfo(vehicle) {
        const info = `${vehicle.year || ''} ${vehicle.make || ''} ${vehicle.model || ''}`.trim();
        return this.escapeHtml(info || 'Unknown Vehicle');
    }

    toggleRowSelection(row) {
        row.classList.toggle('table-active');
        // Could emit events for bulk operations
    }

    renderSearchResults(results, query) {
        // Implementation for search results rendering
        this.renderVehicles(results, `Search: "${query}"`);
    }

    updateVehicleInView(vehicle) {
        const row = document.querySelector(`[data-vehicle-id="${vehicle.towbook_call_number}"]`);
        if (row) {
            // Update the existing row/card with new data
            const newRow = this.createVehicleRow(vehicle);
            row.replaceWith(newRow);
        }
    }

    addVehicleToView(vehicle) {
        // Add new vehicle to current view if it matches filter
        const tbody = document.querySelector('.vehicle-table tbody');
        if (tbody && !tbody.querySelector('.text-center')) {
            const newRow = this.createVehicleRow(vehicle);
            tbody.appendChild(newRow);
        }
    }

    removeVehicleFromView(callNumber) {
        const element = document.querySelector(`[data-vehicle-id="${callNumber}"]`);
        if (element) {
            element.remove();
        }
    }
}

/**
 * VehicleTemplates - Template management for vehicle rendering
 */
class VehicleTemplates {
    constructor() {
        this.templates = new Map();
    }

    // Template methods can be added here for more complex rendering
    getTemplate(name) {
        return this.templates.get(name);
    }

    setTemplate(name, template) {
        this.templates.set(name, template);
    }
}

// Export for use in other modules
window.VehicleRenderer = VehicleRenderer;
