/**
 * ModuleManager.js - Integration Module for Professional Architecture
 * 
 * This module provides seamless integration between the new professional modules
 * and the existing main.js system. It handles dependency management, module
 * initialization, and provides a migration path from monolithic to modular.
 */

class ModuleManager {
    constructor() {
        this.modules = new Map();
        this.dependencies = new Map();
        this.initialized = false;
        this.fallbackToLegacy = true; // Gradual migration support
        
        // Initialize module loading
        this.init();
    }

    /**
     * Initialize the module manager
     */
    async init() {
        try {
            console.log('ModuleManager: Initializing professional architecture...');
            
            // Initialize core modules
            await this.initializeModules();
            
            // Setup integration bridges
            this.setupLegacyBridges();
            
            // Setup global event coordination
            this.setupGlobalEvents();
            
            this.initialized = true;
            console.log('ModuleManager: Professional architecture initialized successfully');
            
            // Notify the system that modules are ready
            this.notifyModulesReady();
            
        } catch (error) {
            console.error('ModuleManager: Failed to initialize:', error);
            this.fallbackToLegacy = true;
            this.notifyFallbackMode();
        }
    }

    /**
     * Initialize all professional modules
     */
    async initializeModules() {
        try {
            // Check if modules are available
            if (typeof VehicleManager === 'undefined' || 
                typeof VehicleRenderer === 'undefined' || 
                typeof StatusManager === 'undefined') {
                
                console.warn('ModuleManager: Professional modules not loaded, falling back to legacy mode');
                this.fallbackToLegacy = true;
                return;
            }

            // Initialize modules in dependency order
            console.log('ModuleManager: Initializing VehicleManager...');
            this.modules.set('vehicleManager', new VehicleManager());
            
            console.log('ModuleManager: Initializing StatusManager...');
            this.modules.set('statusManager', new StatusManager());
            
            console.log('ModuleManager: Initializing VehicleRenderer...');
            this.modules.set('vehicleRenderer', new VehicleRenderer(this.modules.get('vehicleManager')));
            
            // Setup inter-module communication
            this.setupModuleCommunication();
            
            this.fallbackToLegacy = false;
            
        } catch (error) {
            console.error('ModuleManager: Error initializing modules:', error);
            throw error;
        }
    }

    /**
     * Setup communication between modules
     */
    setupModuleCommunication() {
        const vehicleManager = this.modules.get('vehicleManager');
        const statusManager = this.modules.get('statusManager');
        const vehicleRenderer = this.modules.get('vehicleRenderer');

        // Connect status manager to vehicle manager
        if (vehicleManager && statusManager) {
            vehicleManager.subscribe((event, data) => {
                if (event === 'vehicleUpdated' && data.statusChanged) {
                    statusManager.handleStatusChange(data.vehicle);
                }
            });
        }

        // Setup global access for legacy compatibility
        window.moduleManager = this;
        window.vehicleManager = vehicleManager;
        window.statusManager = statusManager;
        window.vehicleRenderer = vehicleRenderer;
    }

    /**
     * Setup bridges to legacy functions for gradual migration
     */
    setupLegacyBridges() {
        // Bridge legacy loadVehicles function
        if (typeof window.loadVehicles === 'function') {
            const originalLoadVehicles = window.loadVehicles;
            window.loadVehicles = (statusFilter, forceRefresh) => {
                if (this.initialized && !this.fallbackToLegacy) {
                    return this.loadVehiclesModern(statusFilter, forceRefresh);
                } else {
                    return originalLoadVehicles(statusFilter, forceRefresh);
                }
            };
        }

        // Bridge legacy renderVehicleTable function
        if (typeof window.renderVehicleTable === 'function') {
            const originalRenderVehicleTable = window.renderVehicleTable;
            window.renderVehicleTable = (vehicles, currentFilterName) => {
                if (this.initialized && !this.fallbackToLegacy) {
                    return this.renderVehicleTableModern(vehicles, currentFilterName);
                } else {
                    return originalRenderVehicleTable(vehicles, currentFilterName);
                }
            };
        }

        // Bridge vehicle editing functions
        this.bridgeVehicleEditingFunctions();
        
        // Bridge status management functions
        this.bridgeStatusManagementFunctions();
    }

    /**
     * Modern implementation of loadVehicles using professional modules
     */
    async loadVehiclesModern(statusFilter = 'active', forceRefresh = false) {
        try {
            if (typeof window.showLoading === 'function') {
                window.showLoading('Loading vehicles...');
            }

            const vehicleManager = this.modules.get('vehicleManager');
            const vehicles = await vehicleManager.loadVehicles(statusFilter, forceRefresh);
            
            // Update global state for legacy compatibility
            if (window.appState) {
                window.appState.vehiclesData = vehicles;
                window.appState.lastVehicleTab = statusFilter;
            }

            console.log(`ModuleManager: Loaded ${vehicles.length} vehicles using modern architecture`);
            return vehicles;

        } catch (error) {
            console.error('ModuleManager: Error in modern loadVehicles:', error);
            // Fallback to legacy implementation
            if (typeof window.loadVehicles === 'function') {
                return window.loadVehicles.original(statusFilter, forceRefresh);
            }
            throw error;
        } finally {
            if (typeof window.hideLoading === 'function') {
                window.hideLoading();
            }
        }
    }

    /**
     * Modern implementation of renderVehicleTable using professional modules
     */
    renderVehicleTableModern(vehicles, currentFilterName) {
        try {
            const vehicleRenderer = this.modules.get('vehicleRenderer');
            vehicleRenderer.renderVehicles(vehicles, currentFilterName);
            
            console.log(`ModuleManager: Rendered ${vehicles.length} vehicles using modern architecture`);
            
        } catch (error) {
            console.error('ModuleManager: Error in modern renderVehicleTable:', error);
            // Fallback to legacy implementation
            if (typeof window.renderVehicleTable === 'function') {
                return window.renderVehicleTable.original(vehicles, currentFilterName);
            }
            throw error;
        }
    }

    /**
     * Bridge vehicle editing functions
     */
    bridgeVehicleEditingFunctions() {
        // Bridge openEditVehicleModal
        if (typeof window.openEditVehicleModal === 'function') {
            const original = window.openEditVehicleModal;
            window.openEditVehicleModal = (callNumber) => {
                if (this.initialized && !this.fallbackToLegacy) {
                    const vehicleManager = this.modules.get('vehicleManager');
                    const vehicle = vehicleManager.getVehicle(callNumber);
                    if (vehicle) {
                        return this.openEditVehicleModalModern(vehicle);
                    }
                }
                return original(callNumber);
            };
        }

        // Bridge saveVehicleChanges
        if (typeof window.saveVehicleChanges === 'function') {
            const original = window.saveVehicleChanges;
            window.saveVehicleChanges = async (callNumber) => {
                if (this.initialized && !this.fallbackToLegacy) {
                    return this.saveVehicleChangesModern(callNumber);
                }
                return original(callNumber);
            };
        }

        // Bridge vehicle deletion
        if (typeof window.deleteVehicle === 'function') {
            const original = window.deleteVehicle;
            window.deleteVehicle = async (callNumber) => {
                if (this.initialized && !this.fallbackToLegacy) {
                    const vehicleManager = this.modules.get('vehicleManager');
                    return vehicleManager.deleteVehicle(callNumber);
                }
                return original(callNumber);
            };
        }
    }

    /**
     * Bridge status management functions
     */
    bridgeStatusManagementFunctions() {
        // Create a global function for status updates
        window.updateVehicleStatusModern = async (callNumber, newStatus, additionalData = {}) => {
            if (!this.initialized || this.fallbackToLegacy) {
                throw new Error('Modern status management not available');
            }

            const statusManager = this.modules.get('statusManager');
            const vehicleManager = this.modules.get('vehicleManager');
            
            const vehicle = vehicleManager.getVehicle(callNumber);
            if (!vehicle) {
                throw new Error(`Vehicle ${callNumber} not found`);
            }

            return statusManager.updateVehicleStatus(callNumber, newStatus, vehicle, additionalData);
        };
    }

    /**
     * Modern edit modal implementation
     */
    openEditVehicleModalModern(vehicle) {
        try {
            const modal = document.getElementById('editVehicleModal');
            if (!modal) {
                console.error('Edit vehicle modal not found');
                return;
            }

            // Use modern data binding
            this.populateEditModal(vehicle);

            // Setup modern event handlers
            this.setupEditModalEvents(vehicle.towbook_call_number);

            // Show modal
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();

        } catch (error) {
            console.error('ModuleManager: Error opening modern edit modal:', error);
            // Fallback to legacy
            if (typeof window.openEditVehicleModal === 'function') {
                window.openEditVehicleModal.original(vehicle.towbook_call_number);
            }
        }
    }

    /**
     * Modern save vehicle changes implementation
     */
    async saveVehicleChangesModern(callNumber) {
        try {
            if (typeof window.showLoading === 'function') {
                window.showLoading('Saving changes...');
            }

            const vehicleManager = this.modules.get('vehicleManager');
            const formData = this.collectFormData('editVehicleForm');
            
            const updatedVehicle = await vehicleManager.updateVehicle(callNumber, formData);

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editVehicleModal'));
            if (modal) {
                modal.hide();
            }

            // Show success message
            if (typeof window.showToast === 'function') {
                window.showToast('Vehicle updated successfully!', 'success');
            }

            // Refresh current view
            this.refreshCurrentView();

            return updatedVehicle;

        } catch (error) {
            console.error('ModuleManager: Error saving vehicle changes:', error);
            if (typeof window.showToast === 'function') {
                window.showToast('Error updating vehicle: ' + error.message, 'error');
            }
            throw error;
        } finally {
            if (typeof window.hideLoading === 'function') {
                window.hideLoading();
            }
        }
    }

    /**
     * Setup global event coordination
     */
    setupGlobalEvents() {
        // Listen for tab changes
        document.addEventListener('tabChanged', (event) => {
            this.handleTabChange(event.detail);
        });

        // Listen for vehicle data changes
        document.addEventListener('vehicleDataChanged', (event) => {
            this.handleVehicleDataChange(event.detail);
        });

        // Setup periodic health checks
        setInterval(() => {
            this.performHealthCheck();
        }, 30000); // Every 30 seconds
    }

    /**
     * Handle tab changes in the application
     */
    handleTabChange(tabInfo) {
        console.log('ModuleManager: Tab changed to:', tabInfo.tab);
        
        // Reset module states if needed
        if (tabInfo.tab.startsWith('vehicles-')) {
            const statusFilter = tabInfo.tab.replace('vehicles-', '');
            this.preloadVehicleData(statusFilter);
        }
    }

    /**
     * Preload vehicle data for performance
     */
    async preloadVehicleData(statusFilter) {
        try {
            if (this.initialized && !this.fallbackToLegacy) {
                const vehicleManager = this.modules.get('vehicleManager');
                await vehicleManager.loadVehicles(statusFilter);
            }
        } catch (error) {
            console.warn('ModuleManager: Failed to preload vehicle data:', error);
        }
    }

    /**
     * Perform health check on modules
     */
    performHealthCheck() {
        if (!this.initialized) return;

        try {
            // Check if modules are still responsive
            this.modules.forEach((module, name) => {
                if (typeof module.getStatistics === 'function') {
                    const stats = module.getStatistics();
                    console.debug(`ModuleManager: ${name} health check - ${JSON.stringify(stats)}`);
                }
            });
        } catch (error) {
            console.warn('ModuleManager: Health check failed:', error);
        }
    }

    /**
     * Utility methods
     */
    populateEditModal(vehicle) {
        // Modern data binding for edit modal
        const fields = [
            'vin', 'year', 'make', 'model', 'color', 'vehicle_type',
            'plate', 'state', 'tow_date', 'tow_time', 'status',
            'complaint_number', 'location', 'requestor', 'reason_for_tow',
            'jurisdiction', 'officer_name', 'case_number', 'owner_name',
            'owner_address', 'owner_phone', 'owner_email',
            'lienholder_name', 'lienholder_address', 'notes'
        ];

        fields.forEach(field => {
            const element = document.getElementById(`edit-${field}`);
            if (element) {
                element.value = vehicle[field] || '';
            }
        });

        document.getElementById('edit-vehicle-id').value = vehicle.towbook_call_number;
    }

    setupEditModalEvents(callNumber) {
        const saveButton = document.getElementById('saveVehicleChangesButton');
        if (saveButton) {
            saveButton.onclick = () => this.saveVehicleChangesModern(callNumber);
        }
    }

    collectFormData(formId) {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            if (value && value.trim() !== '') {
                data[key] = value.trim();
            }
        }
        
        return data;
    }

    refreshCurrentView() {
        if (window.appState && window.appState.currentTab) {
            const currentTab = window.appState.currentTab;
            if (currentTab.includes('vehicles-')) {
                const statusFilter = currentTab.replace('vehicles-', '') || 'active';
                this.loadVehiclesModern(statusFilter, true);
            } else if (currentTab === 'dashboard') {
                if (typeof window.loadTab === 'function') {
                    window.loadTab('dashboard', true);
                }
            }
        }
    }

    /**
     * Notify system that modules are ready
     */
    notifyModulesReady() {
        document.dispatchEvent(new CustomEvent('modulesReady', {
            detail: {
                modules: Array.from(this.modules.keys()),
                fallbackMode: this.fallbackToLegacy
            }
        }));

        // Update any loading indicators
        const loader = document.getElementById('module-loader');
        if (loader) {
            loader.style.display = 'none';
        }
    }

    /**
     * Notify system of fallback mode
     */
    notifyFallbackMode() {
        console.warn('ModuleManager: Running in legacy fallback mode');
        
        document.dispatchEvent(new CustomEvent('modulesFallback', {
            detail: {
                reason: 'Module initialization failed',
                fallbackMode: true
            }
        }));
    }

    /**
     * Get module instance
     */
    getModule(name) {
        return this.modules.get(name);
    }

    /**
     * Check if modern architecture is available
     */
    isModernAvailable() {
        return this.initialized && !this.fallbackToLegacy;
    }

    /**
     * Get system status
     */
    getStatus() {
        return {
            initialized: this.initialized,
            fallbackMode: this.fallbackToLegacy,
            modules: Array.from(this.modules.keys()),
            moduleCount: this.modules.size
        };
    }

    /**
     * Cleanup resources
     */
    destroy() {
        this.modules.forEach(module => {
            if (typeof module.destroy === 'function') {
                module.destroy();
            }
        });
        
        this.modules.clear();
        this.dependencies.clear();
        this.initialized = false;
        
        console.log('ModuleManager: Destroyed');
    }
}

// Initialize the module manager when script loads
window.addEventListener('DOMContentLoaded', () => {
    console.log('ModuleManager: DOM loaded, initializing...');
    window.moduleManager = new ModuleManager();
});

// Export for use in other modules
window.ModuleManager = ModuleManager;
