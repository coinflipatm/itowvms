/**
 * VehicleManager.js - Professional Vehicle Management Module
 * 
 * This module provides a centralized, robust way to manage vehicle data,
 * API interactions, and state management. Follows professional coding practices
 * and is designed to be maintainable and extensible.
 */

class VehicleManager {
    constructor() {
        this.vehicles = new Map(); // Use Map for O(1) lookups
        this.currentFilter = 'active';
        this.sortConfig = {
            column: 'tow_date',
            direction: 'desc'
        };
        this.cache = new Map(); // Cache for API responses
        this.subscribers = new Set(); // Observer pattern for state changes
        
        // Bind methods to preserve 'this' context
        this.handleApiError = this.handleApiError.bind(this);
        this.refreshData = this.refreshData.bind(this);
    }

    /**
     * Subscribe to vehicle data changes
     * @param {Function} callback - Function to call when data changes
     */
    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback); // Return unsubscribe function
    }

    /**
     * Notify all subscribers of data changes
     * @param {string} event - Type of change
     * @param {any} data - Changed data
     */
    notifySubscribers(event, data) {
        this.subscribers.forEach(callback => {
            try {
                callback(event, data);
            } catch (error) {
                console.error('Error in vehicle data subscriber:', error);
            }
        });
    }

    /**
     * Load vehicles with robust error handling and caching
     * @param {string} statusFilter - Filter to apply
     * @param {boolean} forceRefresh - Force cache refresh
     * @returns {Promise<Array>} Vehicle data
     */
    async loadVehicles(statusFilter = 'active', forceRefresh = false) {
        const cacheKey = `vehicles_${statusFilter}_${this.sortConfig.column}_${this.sortConfig.direction}`;
        
        try {
            // Check cache first (unless forcing refresh)
            if (!forceRefresh && this.cache.has(cacheKey)) {
                const cachedData = this.cache.get(cacheKey);
                if (Date.now() - cachedData.timestamp < 30000) { // 30 second cache
                    console.log(`Using cached data for ${statusFilter}`);
                    this.updateVehicleMap(cachedData.data);
                    return cachedData.data;
                }
            }

            // Show loading state
            this.notifySubscribers('loading', { filter: statusFilter });

            // Build API URL with proper parameters
            const params = new URLSearchParams({
                status: this.convertFilterToApiStatus(statusFilter),
                sort: this.sortConfig.column,
                direction: this.sortConfig.direction
            });

            const response = await this.makeAuthenticatedRequest(`/api/vehicles?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const vehicles = await response.json();
            
            // Validate and sanitize data
            const sanitizedVehicles = this.sanitizeVehicleData(vehicles);
            
            // Update cache
            this.cache.set(cacheKey, {
                data: sanitizedVehicles,
                timestamp: Date.now()
            });

            // Update internal state
            this.updateVehicleMap(sanitizedVehicles);
            this.currentFilter = statusFilter;

            // Notify subscribers
            this.notifySubscribers('dataLoaded', {
                filter: statusFilter,
                vehicles: sanitizedVehicles,
                count: sanitizedVehicles.length
            });

            return sanitizedVehicles;

        } catch (error) {
            this.handleApiError(error, 'loadVehicles');
            throw error;
        }
    }

    /**
     * Update a vehicle with optimistic updates and rollback capability
     * @param {string} callNumber - Vehicle call number
     * @param {Object} updates - Fields to update
     * @returns {Promise<Object>} Updated vehicle
     */
    async updateVehicle(callNumber, updates) {
        const originalVehicle = this.vehicles.get(callNumber);
        
        if (!originalVehicle) {
            throw new Error(`Vehicle ${callNumber} not found`);
        }

        try {
            // Optimistic update
            const optimisticVehicle = { ...originalVehicle, ...updates };
            this.vehicles.set(callNumber, optimisticVehicle);
            this.notifySubscribers('vehicleUpdated', { 
                callNumber, 
                vehicle: optimisticVehicle,
                optimistic: true 
            });

            // Make API call
            const response = await this.makeAuthenticatedRequest(`/api/vehicles/${callNumber}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updates)
            });

            if (!response.ok) {
                throw new Error(`Failed to update vehicle: ${response.status}`);
            }

            const updatedVehicle = await response.json();
            
            // Replace optimistic update with real data
            this.vehicles.set(callNumber, updatedVehicle);
            this.invalidateCache(); // Clear cache after update
            
            this.notifySubscribers('vehicleUpdated', { 
                callNumber, 
                vehicle: updatedVehicle,
                optimistic: false 
            });

            return updatedVehicle;

        } catch (error) {
            // Rollback optimistic update
            this.vehicles.set(callNumber, originalVehicle);
            this.notifySubscribers('vehicleUpdateFailed', { 
                callNumber, 
                error: error.message,
                originalVehicle 
            });
            
            this.handleApiError(error, 'updateVehicle');
            throw error;
        }
    }

    /**
     * Add a new vehicle with validation
     * @param {Object} vehicleData - New vehicle data
     * @returns {Promise<Object>} Created vehicle
     */
    async addVehicle(vehicleData) {
        try {
            // Validate required fields
            this.validateVehicleData(vehicleData);

            const response = await this.makeAuthenticatedRequest('/api/vehicles', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(vehicleData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `Failed to add vehicle: ${response.status}`);
            }

            const newVehicle = await response.json();
            
            // Add to local state
            this.vehicles.set(newVehicle.towbook_call_number, newVehicle);
            this.invalidateCache();
            
            this.notifySubscribers('vehicleAdded', { vehicle: newVehicle });

            return newVehicle;

        } catch (error) {
            this.handleApiError(error, 'addVehicle');
            throw error;
        }
    }

    /**
     * Delete a vehicle with confirmation
     * @param {string} callNumber - Vehicle call number
     * @returns {Promise<boolean>} Success status
     */
    async deleteVehicle(callNumber) {
        if (!this.vehicles.has(callNumber)) {
            throw new Error(`Vehicle ${callNumber} not found`);
        }

        try {
            const response = await this.makeAuthenticatedRequest(`/api/vehicles/${callNumber}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`Failed to delete vehicle: ${response.status}`);
            }

            // Remove from local state
            const deletedVehicle = this.vehicles.get(callNumber);
            this.vehicles.delete(callNumber);
            this.invalidateCache();
            
            this.notifySubscribers('vehicleDeleted', { 
                callNumber, 
                vehicle: deletedVehicle 
            });

            return true;

        } catch (error) {
            this.handleApiError(error, 'deleteVehicle');
            throw error;
        }
    }

    /**
     * Get vehicle by call number
     * @param {string} callNumber - Vehicle call number
     * @returns {Object|null} Vehicle data
     */
    getVehicle(callNumber) {
        return this.vehicles.get(callNumber) || null;
    }

    /**
     * Get all vehicles for current filter
     * @returns {Array} Vehicles array
     */
    getVehicles() {
        return Array.from(this.vehicles.values());
    }

    /**
     * Sort vehicles by column
     * @param {string} column - Column to sort by
     * @param {string} direction - Sort direction (asc/desc)
     */
    sortVehicles(column, direction = 'asc') {
        this.sortConfig = { column, direction };
        
        const vehicles = Array.from(this.vehicles.values());
        vehicles.sort((a, b) => {
            const aVal = a[column] || '';
            const bVal = b[column] || '';
            
            // Handle date sorting specially
            if (column === 'tow_date') {
                const aDate = new Date(aVal);
                const bDate = new Date(bVal);
                return direction === 'asc' ? aDate - bDate : bDate - aDate;
            }
            
            // String comparison
            const comparison = aVal.toString().localeCompare(bVal.toString());
            return direction === 'asc' ? comparison : -comparison;
        });

        // Update the Map with sorted order
        this.vehicles.clear();
        vehicles.forEach(vehicle => {
            this.vehicles.set(vehicle.towbook_call_number, vehicle);
        });

        this.notifySubscribers('vehiclesSorted', { 
            column, 
            direction, 
            vehicles 
        });
    }

    /**
     * Search vehicles by various criteria
     * @param {string} query - Search query
     * @param {Array} fields - Fields to search in
     * @returns {Array} Matching vehicles
     */
    searchVehicles(query, fields = ['make', 'model', 'vin', 'towbook_call_number', 'complaint_number']) {
        if (!query.trim()) {
            return this.getVehicles();
        }

        const searchTerm = query.toLowerCase();
        const matchingVehicles = this.getVehicles().filter(vehicle => {
            return fields.some(field => {
                const value = vehicle[field];
                return value && value.toString().toLowerCase().includes(searchTerm);
            });
        });

        this.notifySubscribers('searchResults', { 
            query, 
            results: matchingVehicles,
            count: matchingVehicles.length 
        });

        return matchingVehicles;
    }

    // Private helper methods

    /**
     * Convert UI filter to API status parameter
     * @param {string} filter - UI filter name
     * @returns {string} API status
     */
    convertFilterToApiStatus(filter) {
        const filterMap = {
            'active': 'active',
            'completed': 'completed',
            'New': 'New',
            'TOP_Generated': 'TOP Generated',
            'Ready_for_Auction': 'Ready for Auction',
            'Ready_for_Scrap': 'Ready for Scrap',
            'Released': 'Released',
            'Auctioned': 'Auctioned',
            'Scrapped': 'Scrapped'
        };

        return filterMap[filter] || filter;
    }

    /**
     * Update internal vehicle map
     * @param {Array} vehicles - Vehicle array
     */
    updateVehicleMap(vehicles) {
        this.vehicles.clear();
        vehicles.forEach(vehicle => {
            if (vehicle.towbook_call_number) {
                this.vehicles.set(vehicle.towbook_call_number, vehicle);
            }
        });
    }

    /**
     * Sanitize and validate vehicle data
     * @param {Array} vehicles - Raw vehicle data
     * @returns {Array} Sanitized vehicles
     */
    sanitizeVehicleData(vehicles) {
        if (!Array.isArray(vehicles)) {
            console.warn('Expected array of vehicles, got:', typeof vehicles);
            return [];
        }

        return vehicles.map(vehicle => ({
            // Ensure required fields exist
            towbook_call_number: vehicle.towbook_call_number || '',
            complaint_number: vehicle.complaint_number || '',
            status: vehicle.status || 'New',
            tow_date: vehicle.tow_date || '',
            
            // Vehicle info with defaults
            make: vehicle.make || '',
            model: vehicle.model || '',
            year: vehicle.vehicle_year || vehicle.year || '',
            color: vehicle.color || '',
            vin: vehicle.vin || '',
            plate: vehicle.plate || '',
            state: vehicle.state || '',
            vehicle_type: vehicle.vehicle_type || '',
            
            // Location and request info
            location: vehicle.location || '',
            requestor: vehicle.requestor || '',
            reason_for_tow: vehicle.reason_for_tow || '',
            jurisdiction: vehicle.jurisdiction || '',
            
            // Officer and case info
            officer_name: vehicle.officer_name || '',
            case_number: vehicle.case_number || '',
            
            // Owner info
            owner_name: vehicle.owner_name || '',
            owner_address: vehicle.owner_address || '',
            owner_phone: vehicle.owner_phone || '',
            owner_email: vehicle.owner_email || '',
            
            // Lienholder info
            lienholder_name: vehicle.lienholder_name || '',
            lienholder_address: vehicle.lienholder_address || '',
            
            // Additional fields
            notes: vehicle.notes || '',
            ...vehicle // Spread to include any additional fields
        }));
    }

    /**
     * Validate vehicle data before submission
     * @param {Object} vehicleData - Vehicle data to validate
     * @throws {Error} If validation fails
     */
    validateVehicleData(vehicleData) {
        const requiredFields = ['towbook_call_number', 'make', 'model', 'tow_date'];
        const missingFields = requiredFields.filter(field => !vehicleData[field]);
        
        if (missingFields.length > 0) {
            throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
        }

        // Validate date format
        if (vehicleData.tow_date && !this.isValidDate(vehicleData.tow_date)) {
            throw new Error('Invalid tow date format. Expected YYYY-MM-DD');
        }

        // Validate email if provided
        if (vehicleData.owner_email && !this.isValidEmail(vehicleData.owner_email)) {
            throw new Error('Invalid owner email format');
        }

        // Validate phone if provided
        if (vehicleData.owner_phone && !this.isValidPhone(vehicleData.owner_phone)) {
            throw new Error('Invalid owner phone format');
        }
    }

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

        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (response.status === 401) {
            this.notifySubscribers('authenticationError', { url, status: 401 });
            throw new Error('Authentication required');
        }

        return response;
    }

    /**
     * Handle API errors consistently
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     */
    handleApiError(error, operation) {
        console.error(`VehicleManager ${operation} error:`, error);
        
        this.notifySubscribers('error', {
            operation,
            error: error.message,
            timestamp: new Date().toISOString()
        });

        // Show user-friendly error message
        if (typeof showToast === 'function') {
            let message = 'An error occurred. Please try again.';
            
            if (error.message.includes('Authentication')) {
                message = 'Your session has expired. Please refresh the page.';
            } else if (error.message.includes('Network')) {
                message = 'Network error. Please check your connection.';
            } else if (error.message.includes('500')) {
                message = 'Server error. Please contact support if this persists.';
            }
            
            showToast(message, 'error');
        }
    }

    /**
     * Invalidate all cache entries
     */
    invalidateCache() {
        this.cache.clear();
        console.log('Vehicle cache invalidated');
    }

    /**
     * Utility methods
     */
    isValidDate(dateString) {
        const date = new Date(dateString);
        return date instanceof Date && !isNaN(date);
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    isValidPhone(phone) {
        const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
        return phoneRegex.test(phone.replace(/\D/g, ''));
    }

    /**
     * Get statistics about current vehicle data
     * @returns {Object} Statistics object
     */
    getStatistics() {
        const vehicles = this.getVehicles();
        const statusCounts = {};
        
        vehicles.forEach(vehicle => {
            const status = vehicle.status || 'Unknown';
            statusCounts[status] = (statusCounts[status] || 0) + 1;
        });

        return {
            total: vehicles.length,
            statusCounts,
            filter: this.currentFilter,
            lastUpdated: new Date().toISOString()
        };
    }

    /**
     * Clean up resources
     */
    destroy() {
        this.vehicles.clear();
        this.cache.clear();
        this.subscribers.clear();
        console.log('VehicleManager destroyed');
    }
}

// Export for use in other modules
window.VehicleManager = VehicleManager;
