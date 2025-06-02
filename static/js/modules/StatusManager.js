/**
 * StatusManager.js - Professional Status Management Module
 * 
 * Handles all vehicle status-related operations with proper validation,
 * business rules, and state management.
 */

class StatusManager {
    constructor() {
        // Define valid status transitions and business rules
        this.statusDefinitions = this.initializeStatusDefinitions();
        this.transitionRules = this.initializeTransitionRules();
        this.statusRequirements = this.initializeStatusRequirements();
        
        // Event listeners
        this.subscribers = new Set();
        
        // Bind methods
        this.validateStatusTransition = this.validateStatusTransition.bind(this);
        this.updateVehicleStatus = this.updateVehicleStatus.bind(this);
    }

    /**
     * Initialize status definitions with metadata
     * @returns {Map} Status definitions
     */
    initializeStatusDefinitions() {
        const statuses = new Map();
        
        statuses.set('New', {
            label: 'New',
            description: 'Vehicle just towed, paperwork started',
            color: '#007bff',
            icon: 'fas fa-plus-circle',
            category: 'active',
            order: 1,
            isActive: true,
            allowEdit: true,
            allowDelete: true
        });

        statuses.set('TOP Generated', {
            label: 'TOP Generated',
            description: 'Tow Owner Package generated, legal notices sent',
            color: '#17a2b8',
            icon: 'fas fa-file-signature',
            category: 'active',
            order: 2,
            isActive: true,
            allowEdit: true,
            allowDelete: false
        });

        statuses.set('Ready for Auction', {
            label: 'Ready for Auction',
            description: 'Vehicle ready for auction process',
            color: '#ffc107',
            icon: 'fas fa-gavel',
            category: 'active',
            order: 3,
            isActive: true,
            allowEdit: true,
            allowDelete: false
        });

        statuses.set('Ready for Scrap', {
            label: 'Ready for Scrap',
            description: 'Vehicle ready for scrap process',
            color: '#fd7e14',
            icon: 'fas fa-recycle',
            category: 'active',
            order: 4,
            isActive: true,
            allowEdit: true,
            allowDelete: false
        });

        statuses.set('Released', {
            label: 'Released',
            description: 'Vehicle released to owner',
            color: '#6c757d',
            icon: 'fas fa-check-circle',
            category: 'completed',
            order: 5,
            isActive: false,
            allowEdit: false,
            allowDelete: false
        });

        statuses.set('Auctioned', {
            label: 'Auctioned',
            description: 'Vehicle sold at auction',
            color: '#28a745',
            icon: 'fas fa-handshake',
            category: 'completed',
            order: 6,
            isActive: false,
            allowEdit: false,
            allowDelete: false
        });

        statuses.set('Scrapped', {
            label: 'Scrapped',
            description: 'Vehicle scrapped/destroyed',
            color: '#dc3545',
            icon: 'fas fa-tools',
            category: 'completed',
            order: 7,
            isActive: false,
            allowEdit: false,
            allowDelete: false
        });

        statuses.set('Transferred', {
            label: 'Transferred',
            description: 'Vehicle transferred to another jurisdiction',
            color: '#6f42c1',
            icon: 'fas fa-exchange-alt',
            category: 'completed',
            order: 8,
            isActive: false,
            allowEdit: false,
            allowDelete: false
        });

        return statuses;
    }

    /**
     * Initialize status transition rules
     * @returns {Map} Transition rules
     */
    initializeTransitionRules() {
        const rules = new Map();

        // Define valid transitions for each status
        rules.set('New', [
            'TOP Generated',
            'Released',
            'Transferred'
        ]);

        rules.set('TOP Generated', [
            'Ready for Auction',
            'Ready for Scrap',
            'Released',
            'Transferred'
        ]);

        rules.set('Ready for Auction', [
            'Auctioned',
            'Ready for Scrap',
            'Released',
            'Transferred'
        ]);

        rules.set('Ready for Scrap', [
            'Scrapped',
            'Ready for Auction',
            'Released',
            'Transferred'
        ]);

        // Terminal states (no transitions allowed)
        rules.set('Released', []);
        rules.set('Auctioned', []);
        rules.set('Scrapped', []);
        rules.set('Transferred', []);

        return rules;
    }

    /**
     * Initialize status requirements (business rules)
     * @returns {Map} Status requirements
     */
    initializeStatusRequirements() {
        const requirements = new Map();

        requirements.set('TOP Generated', {
            requiredFields: ['owner_name', 'owner_address'],
            minimumDays: 0,
            requiredDocuments: ['TOP'],
            validation: (vehicle) => {
                if (!vehicle.owner_name || !vehicle.owner_address) {
                    return { valid: false, message: 'Owner information required for TOP generation' };
                }
                return { valid: true };
            }
        });

        requirements.set('Ready for Auction', {
            requiredFields: ['tow_date'],
            minimumDays: 10, // Must be in lot for at least 10 days
            requiredDocuments: ['TOP'],
            validation: (vehicle) => {
                const daysSinceTow = this.calculateDaysSince(vehicle.tow_date);
                if (daysSinceTow < 10) {
                    return { 
                        valid: false, 
                        message: `Vehicle must be in lot for at least 10 days (currently ${daysSinceTow} days)` 
                    };
                }
                return { valid: true };
            }
        });

        requirements.set('Ready for Scrap', {
            requiredFields: ['tow_date'],
            minimumDays: 30, // Must be in lot for at least 30 days
            requiredDocuments: ['TOP'],
            validation: (vehicle) => {
                const daysSinceTow = this.calculateDaysSince(vehicle.tow_date);
                if (daysSinceTow < 30) {
                    return { 
                        valid: false, 
                        message: `Vehicle must be in lot for at least 30 days (currently ${daysSinceTow} days)` 
                    };
                }
                return { valid: true };
            }
        });

        requirements.set('Released', {
            requiredFields: ['owner_name'],
            validation: (vehicle) => {
                if (!vehicle.owner_name) {
                    return { valid: false, message: 'Owner information required for release' };
                }
                return { valid: true };
            }
        });

        return requirements;
    }

    /**
     * Subscribe to status change events
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback);
    }

    /**
     * Notify subscribers of status changes
     * @param {string} event - Event type
     * @param {any} data - Event data
     */
    notifySubscribers(event, data) {
        this.subscribers.forEach(callback => {
            try {
                callback(event, data);
            } catch (error) {
                console.error('Error in status change subscriber:', error);
            }
        });
    }

    /**
     * Get all status definitions
     * @returns {Array} Array of status definitions
     */
    getAllStatuses() {
        return Array.from(this.statusDefinitions.values())
            .sort((a, b) => a.order - b.order);
    }

    /**
     * Get status definition by name
     * @param {string} status - Status name
     * @returns {Object|null} Status definition
     */
    getStatusDefinition(status) {
        return this.statusDefinitions.get(status) || null;
    }

    /**
     * Get statuses by category
     * @param {string} category - Category ('active', 'completed')
     * @returns {Array} Filtered statuses
     */
    getStatusesByCategory(category) {
        return this.getAllStatuses().filter(status => status.category === category);
    }

    /**
     * Get valid transitions for a status
     * @param {string} currentStatus - Current status
     * @returns {Array} Valid next statuses
     */
    getValidTransitions(currentStatus) {
        const validStatuses = this.transitionRules.get(currentStatus) || [];
        return validStatuses.map(status => this.getStatusDefinition(status));
    }

    /**
     * Validate if a status transition is allowed
     * @param {string} fromStatus - Current status
     * @param {string} toStatus - Target status
     * @param {Object} vehicle - Vehicle data
     * @returns {Object} Validation result
     */
    validateStatusTransition(fromStatus, toStatus, vehicle) {
        try {
            // Check if transition is allowed by rules
            const validTransitions = this.transitionRules.get(fromStatus) || [];
            if (!validTransitions.includes(toStatus)) {
                return {
                    valid: false,
                    message: `Cannot transition from ${fromStatus} to ${toStatus}`,
                    code: 'INVALID_TRANSITION'
                };
            }

            // Check status requirements
            const requirements = this.statusRequirements.get(toStatus);
            if (requirements) {
                // Check required fields
                if (requirements.requiredFields) {
                    for (const field of requirements.requiredFields) {
                        if (!vehicle[field]) {
                            return {
                                valid: false,
                                message: `Required field missing: ${field}`,
                                code: 'MISSING_REQUIRED_FIELD',
                                field: field
                            };
                        }
                    }
                }

                // Check minimum days requirement
                if (requirements.minimumDays && vehicle.tow_date) {
                    const daysSinceTow = this.calculateDaysSince(vehicle.tow_date);
                    if (daysSinceTow < requirements.minimumDays) {
                        return {
                            valid: false,
                            message: `Vehicle must be in lot for at least ${requirements.minimumDays} days (currently ${daysSinceTow} days)`,
                            code: 'INSUFFICIENT_DAYS',
                            required: requirements.minimumDays,
                            current: daysSinceTow
                        };
                    }
                }

                // Run custom validation
                if (requirements.validation) {
                    const customResult = requirements.validation(vehicle);
                    if (!customResult.valid) {
                        return {
                            valid: false,
                            message: customResult.message,
                            code: 'CUSTOM_VALIDATION_FAILED'
                        };
                    }
                }
            }

            return { valid: true };

        } catch (error) {
            console.error('Error validating status transition:', error);
            return {
                valid: false,
                message: 'Error validating status transition',
                code: 'VALIDATION_ERROR'
            };
        }
    }

    /**
     * Update vehicle status with validation and logging
     * @param {string} callNumber - Vehicle call number
     * @param {string} newStatus - New status
     * @param {Object} vehicle - Current vehicle data
     * @param {Object} options - Additional options
     * @returns {Promise<Object>} Update result
     */
    async updateVehicleStatus(callNumber, newStatus, vehicle, options = {}) {
        try {
            const currentStatus = vehicle.status;
            
            // Validate transition
            const validation = this.validateStatusTransition(currentStatus, newStatus, vehicle);
            if (!validation.valid) {
                throw new Error(validation.message);
            }

            // Prepare update data
            const updateData = {
                status: newStatus,
                status_updated_at: new Date().toISOString(),
                ...options.additionalData
            };

            // Add status-specific data
            const statusSpecificData = this.getStatusSpecificData(newStatus, vehicle);
            Object.assign(updateData, statusSpecificData);

            // Make API call
            const response = await this.makeAuthenticatedRequest(`/api/vehicles/${callNumber}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `Failed to update status: ${response.status}`);
            }

            const updatedVehicle = await response.json();

            // Log the status change
            await this.logStatusChange(callNumber, currentStatus, newStatus, options.reason);

            // Notify subscribers
            this.notifySubscribers('statusChanged', {
                callNumber,
                fromStatus: currentStatus,
                toStatus: newStatus,
                vehicle: updatedVehicle,
                timestamp: new Date().toISOString()
            });

            return {
                success: true,
                vehicle: updatedVehicle,
                message: `Status updated from ${currentStatus} to ${newStatus}`
            };

        } catch (error) {
            console.error('Error updating vehicle status:', error);
            
            this.notifySubscribers('statusUpdateFailed', {
                callNumber,
                status: newStatus,
                error: error.message,
                timestamp: new Date().toISOString()
            });

            throw error;
        }
    }

    /**
     * Get status-specific data for updates
     * @param {string} status - Target status
     * @param {Object} vehicle - Vehicle data
     * @returns {Object} Additional data for the status
     */
    getStatusSpecificData(status, vehicle) {
        const data = {};

        switch (status) {
            case 'TOP Generated':
                data.top_generated_date = new Date().toISOString().split('T')[0];
                break;
            
            case 'Ready for Auction':
                data.auction_ready_date = new Date().toISOString().split('T')[0];
                break;
            
            case 'Ready for Scrap':
                data.scrap_ready_date = new Date().toISOString().split('T')[0];
                break;
            
            case 'Released':
                data.release_date = new Date().toISOString().split('T')[0];
                break;
            
            case 'Auctioned':
                data.auction_date = new Date().toISOString().split('T')[0];
                break;
            
            case 'Scrapped':
                data.scrap_date = new Date().toISOString().split('T')[0];
                break;
        }

        return data;
    }

    /**
     * Log status change for audit trail
     * @param {string} callNumber - Vehicle call number
     * @param {string} fromStatus - Previous status
     * @param {string} toStatus - New status
     * @param {string} reason - Reason for change
     */
    async logStatusChange(callNumber, fromStatus, toStatus, reason) {
        try {
            await this.makeAuthenticatedRequest('/api/logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    vehicle_id: callNumber,
                    action: 'status_change',
                    details: `Status changed from ${fromStatus} to ${toStatus}`,
                    reason: reason || 'User initiated',
                    timestamp: new Date().toISOString()
                })
            });
        } catch (error) {
            console.error('Error logging status change:', error);
            // Don't throw here - logging failure shouldn't prevent status update
        }
    }

    /**
     * Calculate days since a given date
     * @param {string} dateStr - Date string
     * @returns {number} Number of days
     */
    calculateDaysSince(dateStr) {
        if (!dateStr) return 0;
        
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        } catch (error) {
            return 0;
        }
    }

    /**
     * Get vehicles due for status advancement
     * @returns {Promise<Array>} Vehicles ready for advancement
     */
    async getVehiclesDueForAdvancement() {
        try {
            const response = await this.makeAuthenticatedRequest('/api/vehicles/due-for-advancement');
            
            if (!response.ok) {
                throw new Error(`Failed to fetch due vehicles: ${response.status}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Error fetching vehicles due for advancement:', error);
            return [];
        }
    }

    /**
     * Bulk update statuses
     * @param {Array} updates - Array of {callNumber, newStatus, reason}
     * @returns {Promise<Object>} Bulk update result
     */
    async bulkUpdateStatuses(updates) {
        const results = {
            successful: [],
            failed: []
        };

        for (const update of updates) {
            try {
                const vehicle = await this.getVehicleData(update.callNumber);
                const result = await this.updateVehicleStatus(
                    update.callNumber,
                    update.newStatus,
                    vehicle,
                    { reason: update.reason }
                );
                results.successful.push(result);
            } catch (error) {
                results.failed.push({
                    callNumber: update.callNumber,
                    error: error.message
                });
            }
        }

        this.notifySubscribers('bulkStatusUpdate', results);
        return results;
    }

    /**
     * Get status workflow recommendations
     * @param {Object} vehicle - Vehicle data
     * @returns {Array} Recommended next steps
     */
    getWorkflowRecommendations(vehicle) {
        const recommendations = [];
        const currentStatus = vehicle.status;
        const daysSinceTow = this.calculateDaysSince(vehicle.tow_date);

        // Get valid transitions
        const validTransitions = this.getValidTransitions(currentStatus);

        validTransitions.forEach(statusDef => {
            const requirements = this.statusRequirements.get(statusDef.label);
            let recommendation = {
                status: statusDef.label,
                description: statusDef.description,
                priority: 'normal',
                canExecute: true,
                blockers: []
            };

            if (requirements) {
                // Check if requirements are met
                const validation = this.validateStatusTransition(currentStatus, statusDef.label, vehicle);
                
                if (!validation.valid) {
                    recommendation.canExecute = false;
                    recommendation.blockers.push(validation.message);
                } else if (requirements.minimumDays) {
                    // Set priority based on how overdue the transition is
                    const daysOver = daysSinceTow - requirements.minimumDays;
                    if (daysOver > 7) {
                        recommendation.priority = 'high';
                    } else if (daysOver > 0) {
                        recommendation.priority = 'medium';
                    }
                }
            }

            recommendations.push(recommendation);
        });

        return recommendations.sort((a, b) => {
            const priorityOrder = { high: 3, medium: 2, normal: 1 };
            return priorityOrder[b.priority] - priorityOrder[a.priority];
        });
    }

    /**
     * Generate status report
     * @param {string} filter - Filter criteria
     * @returns {Promise<Object>} Status report
     */
    async generateStatusReport(filter = 'all') {
        try {
            const response = await this.makeAuthenticatedRequest(`/api/reports/status?filter=${filter}`);
            
            if (!response.ok) {
                throw new Error(`Failed to generate status report: ${response.status}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Error generating status report:', error);
            throw error;
        }
    }

    // Utility methods

    /**
     * Make authenticated API request
     * @param {string} url - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>} Fetch response
     */
    async makeAuthenticatedRequest(url, options = {}) {
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            }
        };

        return fetch(url, { ...defaultOptions, ...options });
    }

    /**
     * Get vehicle data (placeholder for integration)
     * @param {string} callNumber - Vehicle call number
     * @returns {Promise<Object>} Vehicle data
     */
    async getVehicleData(callNumber) {
        const response = await this.makeAuthenticatedRequest(`/api/vehicles/${callNumber}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch vehicle data: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * Get CSS class for status badge
     * @param {string} status - Status name
     * @returns {string} CSS class
     */
    getStatusCssClass(status) {
        const statusDef = this.getStatusDefinition(status);
        if (statusDef) {
            // Convert color to Bootstrap class
            const colorMap = {
                '#007bff': 'bg-primary',
                '#17a2b8': 'bg-info',
                '#ffc107': 'bg-warning text-dark',
                '#fd7e14': 'bg-warning text-dark',
                '#6c757d': 'bg-secondary',
                '#28a745': 'bg-success',
                '#dc3545': 'bg-danger',
                '#6f42c1': 'bg-primary'
            };
            return colorMap[statusDef.color] || 'bg-secondary';
        }
        return 'bg-secondary';
    }

    /**
     * Format status for display
     * @param {string} status - Status name
     * @returns {string} Formatted status
     */
    formatStatus(status) {
        const statusDef = this.getStatusDefinition(status);
        return statusDef ? statusDef.label : status;
    }

    /**
     * Check if status allows editing
     * @param {string} status - Status name
     * @returns {boolean} Whether editing is allowed
     */
    allowsEditing(status) {
        const statusDef = this.getStatusDefinition(status);
        return statusDef ? statusDef.allowEdit : false;
    }

    /**
     * Check if status allows deletion
     * @param {string} status - Status name
     * @returns {boolean} Whether deletion is allowed
     */
    allowsDeletion(status) {
        const statusDef = this.getStatusDefinition(status);
        return statusDef ? statusDef.allowDelete : false;
    }

    /**
     * Get status filter mapping for API
     * @param {string} uiFilter - UI filter name
     * @returns {Array} Status names for API
     */
    getStatusesForFilter(uiFilter) {
        switch (uiFilter) {
            case 'active':
                return this.getStatusesByCategory('active').map(s => s.label);
            case 'completed':
                return this.getStatusesByCategory('completed').map(s => s.label);
            default:
                // Specific status
                return [uiFilter.replace(/_/g, ' ')];
        }
    }
}

// Export for use in other modules
window.StatusManager = StatusManager;
