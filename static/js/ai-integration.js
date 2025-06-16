/**
 * AI Integration Module for iTow VMS Frontend
 * 
 * Provides JavaScript interfaces for AI-powered features in the web interface.
 * Handles real-time AI suggestions, smart search, and automated workflows.
 */

class AIIntegration {
    constructor() {
        this.baseUrl = '/api/ai';
        this.cache = new Map();
        this.cacheTimeout = 300000; // 5 minutes
        this.isEnabled = true;
        this.subscribers = new Set();
        
        // Initialize AI features
        this.init();
    }
    
    /**
     * Initialize AI integration
     */
    async init() {
        try {
            // Check AI system status
            const status = await this.getSystemStatus();
            this.isEnabled = status.success && status.overall_status === 'healthy';
            
            if (this.isEnabled) {
                console.log('AI Integration: System ready');
                this.setupEventListeners();
                this.startBackgroundTasks();
            } else {
                console.warn('AI Integration: System not available');
            }
        } catch (error) {
            console.error('AI Integration: Failed to initialize', error);
            this.isEnabled = false;
        }
    }
    
    /**
     * Setup event listeners for AI features
     */
    setupEventListeners() {
        // Smart search enhancement
        this.enhanceSearchInputs();
        
        // Auto-suggestions for forms
        this.enhanceFormInputs();
        
        // Real-time vehicle insights
        this.enhanceVehicleViews();
        
        // Document upload AI processing
        this.enhanceDocumentUploads();
    }
    
    /**
     * Start background tasks for AI features
     */
    startBackgroundTasks() {
        // Periodic cache cleanup
        setInterval(() => this.cleanupCache(), 60000); // Every minute
        
        // Periodic system health check
        setInterval(() => this.checkSystemHealth(), 300000); // Every 5 minutes
    }
    
    // ================================================================
    // CORE AI API METHODS
    // ================================================================
    
    /**
     * Make authenticated request to AI API
     */
    async makeRequest(endpoint, options = {}) {
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        const requestOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, requestOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error(`AI API Error (${endpoint}):`, error);
            throw error;
        }
    }
    
    /**
     * Get AI system status
     */
    async getSystemStatus() {
        const cacheKey = 'system_status';
        const cached = this.getFromCache(cacheKey);
        if (cached) return cached;
        
        const status = await this.makeRequest('/status');
        this.setCache(cacheKey, status, 60000); // Cache for 1 minute
        return status;
    }
    
    /**
     * Check system health periodically
     */
    async checkSystemHealth() {
        try {
            const status = await this.getSystemStatus();
            const wasEnabled = this.isEnabled;
            this.isEnabled = status.success && status.overall_status === 'healthy';
            
            if (wasEnabled !== this.isEnabled) {
                this.notifySubscribers('health_changed', { isEnabled: this.isEnabled });
            }
        } catch (error) {
            console.warn('AI Health Check failed:', error);
            this.isEnabled = false;
        }
    }
    
    // ================================================================
    // PREDICTIVE ANALYTICS FEATURES
    // ================================================================
    
    /**
     * Get disposition prediction for a vehicle
     */
    async predictDisposition(vehicleData) {
        if (!this.isEnabled) return null;
        
        const cacheKey = `disposition_${vehicleData.towbook_call_number}`;
        const cached = this.getFromCache(cacheKey);
        if (cached) return cached;
        
        try {
            const result = await this.makeRequest('/predict/disposition', {
                method: 'POST',
                body: JSON.stringify({ vehicle_data: vehicleData })
            });
            
            this.setCache(cacheKey, result);
            return result;
        } catch (error) {
            console.error('Disposition prediction failed:', error);
            return null;
        }
    }
    
    /**
     * Get timeline prediction for a vehicle
     */
    async predictTimeline(vehicleData) {
        if (!this.isEnabled) return null;
        
        try {
            const result = await this.makeRequest('/predict/timeline', {
                method: 'POST',
                body: JSON.stringify({ vehicle_data: vehicleData })
            });
            
            return result;
        } catch (error) {
            console.error('Timeline prediction failed:', error);
            return null;
        }
    }
    
    /**
     * Detect anomalies in vehicle data
     */
    async detectAnomalies(vehicles) {
        if (!this.isEnabled) return {};
        
        try {
            const result = await this.makeRequest('/predict/anomalies', {
                method: 'POST',
                body: JSON.stringify({ vehicles })
            });
            
            return result.anomalies || {};
        } catch (error) {
            console.error('Anomaly detection failed:', error);
            return {};
        }
    }
    
    // ================================================================
    // NATURAL LANGUAGE PROCESSING FEATURES
    // ================================================================
    
    /**
     * Process natural language search query
     */
    async processSearchQuery(query, context = {}) {
        if (!this.isEnabled) return { original_query: query };
        
        try {
            const result = await this.makeRequest('/nlp/query', {
                method: 'POST',
                body: JSON.stringify({ query, context })
            });
            
            return result.result;
        } catch (error) {
            console.error('Query processing failed:', error);
            return { original_query: query };
        }
    }
    
    /**
     * Perform semantic search
     */
    async semanticSearch(query, vehicles, limit = 10) {
        if (!this.isEnabled) return vehicles.slice(0, limit);
        
        try {
            const result = await this.makeRequest('/nlp/search', {
                method: 'POST',
                body: JSON.stringify({ query, vehicles, limit })
            });
            
            return result.results || vehicles.slice(0, limit);
        } catch (error) {
            console.error('Semantic search failed:', error);
            return vehicles.slice(0, limit);
        }
    }
    
    /**
     * Get query suggestions for auto-complete
     */
    async getQuerySuggestions(partialQuery, limit = 5) {
        if (!this.isEnabled || partialQuery.length < 2) return [];
        
        const cacheKey = `suggestions_${partialQuery.toLowerCase()}`;
        const cached = this.getFromCache(cacheKey);
        if (cached) return cached;
        
        try {
            const result = await this.makeRequest('/nlp/suggestions', {
                method: 'POST',
                body: JSON.stringify({ partial_query: partialQuery, limit })
            });
            
            const suggestions = result.suggestions || [];
            this.setCache(cacheKey, suggestions, 600000); // Cache for 10 minutes
            return suggestions;
        } catch (error) {
            console.error('Query suggestions failed:', error);
            return [];
        }
    }
    
    // ================================================================
    // DOCUMENT AI FEATURES
    // ================================================================
    
    /**
     * Process uploaded document with AI
     */
    async processDocument(file) {
        if (!this.isEnabled) return null;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const result = await this.makeRequest('/document/process', {
                method: 'POST',
                headers: {}, // Remove Content-Type to let browser set it for FormData
                body: formData
            });
            
            return result.result;
        } catch (error) {
            console.error('Document processing failed:', error);
            return null;
        }
    }
    
    /**
     * Extract vehicle data from text
     */
    async extractVehicleData(text) {
        if (!this.isEnabled) return {};
        
        try {
            const result = await this.makeRequest('/document/extract', {
                method: 'POST',
                body: JSON.stringify({ text })
            });
            
            return result.extracted_data || {};
        } catch (error) {
            console.error('Data extraction failed:', error);
            return {};
        }
    }
    
    // ================================================================
    // DECISION ENGINE FEATURES
    // ================================================================
    
    /**
     * Get AI workflow decision
     */
    async getWorkflowDecision(vehicleData, currentStage = null) {
        if (!this.isEnabled) return null;
        
        try {
            const result = await this.makeRequest('/decision/workflow', {
                method: 'POST',
                body: JSON.stringify({ vehicle_data: vehicleData, current_stage: currentStage })
            });
            
            return result.routing;
        } catch (error) {
            console.error('Workflow decision failed:', error);
            return null;
        }
    }
    
    /**
     * Get disposition recommendation
     */
    async getDispositionRecommendation(vehicleData) {
        if (!this.isEnabled) return null;
        
        try {
            const result = await this.makeRequest('/decision/disposition', {
                method: 'POST',
                body: JSON.stringify({ vehicle_data: vehicleData })
            });
            
            return result.decision;
        } catch (error) {
            console.error('Disposition recommendation failed:', error);
            return null;
        }
    }
    
    // ================================================================
    // UI ENHANCEMENT FEATURES
    // ================================================================
    
    /**
     * Enhance search inputs with AI suggestions
     */
    enhanceSearchInputs() {
        const searchInputs = document.querySelectorAll('input[type="search"], .search-input, #search-query');
        
        searchInputs.forEach(input => {
            this.addSearchSuggestions(input);
        });
    }
    
    /**
     * Add AI-powered search suggestions to an input
     */
    addSearchSuggestions(input) {
        let suggestionTimeout;
        let suggestionsContainer;
        
        // Create suggestions container
        const createSuggestionsContainer = () => {
            if (suggestionsContainer) return;
            
            suggestionsContainer = document.createElement('div');
            suggestionsContainer.className = 'ai-suggestions';
            suggestionsContainer.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: white;
                border: 1px solid #ddd;
                border-top: none;
                border-radius: 0 0 4px 4px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                max-height: 200px;
                overflow-y: auto;
                z-index: 1000;
                display: none;
            `;
            
            input.parentNode.style.position = 'relative';
            input.parentNode.appendChild(suggestionsContainer);
        };
        
        // Show suggestions
        const showSuggestions = async (query) => {
            if (query.length < 2) {
                if (suggestionsContainer) {
                    suggestionsContainer.style.display = 'none';
                }
                return;
            }
            
            const suggestions = await this.getQuerySuggestions(query);
            
            if (suggestions.length === 0) {
                if (suggestionsContainer) {
                    suggestionsContainer.style.display = 'none';
                }
                return;
            }
            
            createSuggestionsContainer();
            
            suggestionsContainer.innerHTML = suggestions.map(suggestion => 
                `<div class="suggestion-item" style="padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #eee;">
                    ${this.escapeHtml(suggestion)}
                </div>`
            ).join('');
            
            // Add click handlers
            suggestionsContainer.querySelectorAll('.suggestion-item').forEach((item, index) => {
                item.addEventListener('click', () => {
                    input.value = suggestions[index];
                    suggestionsContainer.style.display = 'none';
                    input.dispatchEvent(new Event('change'));
                });
            });
            
            suggestionsContainer.style.display = 'block';
        };
        
        // Input event handler
        input.addEventListener('input', (e) => {
            clearTimeout(suggestionTimeout);
            suggestionTimeout = setTimeout(() => {
                showSuggestions(e.target.value);
            }, 300);
        });
        
        // Hide suggestions on blur
        input.addEventListener('blur', () => {
            setTimeout(() => {
                if (suggestionsContainer) {
                    suggestionsContainer.style.display = 'none';
                }
            }, 200);
        });
    }
    
    /**
     * Enhance vehicle views with AI insights
     */
    enhanceVehicleViews() {
        // Add AI insights to vehicle cards/rows
        const vehicleElements = document.querySelectorAll('[data-vehicle-id]');
        
        vehicleElements.forEach(element => {
            this.addVehicleInsights(element);
        });
    }
    
    /**
     * Add AI insights to a vehicle element
     */
    async addVehicleInsights(element) {
        const vehicleId = element.dataset.vehicleId;
        if (!vehicleId) return;
        
        // Get vehicle data from element or make API call
        const vehicleData = this.extractVehicleDataFromElement(element);
        
        // Get AI predictions
        const predictions = await Promise.allSettled([
            this.predictDisposition(vehicleData),
            this.predictTimeline(vehicleData),
            this.getDispositionRecommendation(vehicleData)
        ]);
        
        // Create insights panel
        const insightsPanel = this.createInsightsPanel(predictions);
        
        // Add to element
        let container = element.querySelector('.ai-insights');
        if (!container) {
            container = document.createElement('div');
            container.className = 'ai-insights';
            element.appendChild(container);
        }
        
        container.innerHTML = insightsPanel;
    }
    
    /**
     * Create AI insights panel HTML
     */
    createInsightsPanel(predictions) {
        const [dispositionResult, timelineResult, recommendationResult] = predictions;
        
        let html = '<div class="ai-insights-panel" style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px; font-size: 12px;">';
        html += '<strong>🤖 AI Insights:</strong><br>';
        
        // Disposition prediction
        if (dispositionResult.status === 'fulfilled' && dispositionResult.value?.prediction) {
            const pred = dispositionResult.value.prediction;
            html += `<span class="ai-insight">📊 Recommended: ${pred.recommendation} (${Math.round(pred.confidence * 100)}% confidence)</span><br>`;
        }
        
        // Timeline prediction
        if (timelineResult.status === 'fulfilled' && timelineResult.value?.prediction) {
            const timeline = timelineResult.value.prediction;
            if (timeline.overall_completion) {
                html += `<span class="ai-insight">⏱️ Est. completion: ${timeline.overall_completion.estimated_days} days</span><br>`;
            }
        }
        
        // Recommendation
        if (recommendationResult.status === 'fulfilled' && recommendationResult.value) {
            const rec = recommendationResult.value;
            html += `<span class="ai-insight">💡 ${rec.decision} - ${rec.reasoning?.substring(0, 50)}...</span>`;
        }
        
        html += '</div>';
        return html;
    }
    
    /**
     * Enhance document upload functionality
     */
    enhanceDocumentUploads() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        
        fileInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.handleDocumentUpload(e.target.files[0], input);
            });
        });
    }
    
    /**
     * Handle document upload with AI processing
     */
    async handleDocumentUpload(file, input) {
        if (!file || !this.isEnabled) return;
        
        // Show processing indicator
        this.showProcessingIndicator(input, 'Processing document with AI...');
        
        try {
            // Process document with AI
            const result = await this.processDocument(file);
            
            if (result && result.extracted_data) {
                // Auto-fill form fields
                this.autoFillFormFields(result.autofill_data || result.extracted_data);
                
                // Show extraction results
                this.showExtractionResults(result, input);
            }
        } catch (error) {
            console.error('Document AI processing failed:', error);
        } finally {
            this.hideProcessingIndicator(input);
        }
    }
    
    /**
     * Auto-fill form fields with extracted data
     */
    autoFillFormFields(data) {
        if (!data || typeof data !== 'object') return;
        
        Object.entries(data).forEach(([key, value]) => {
            if (!value) return;
            
            // Try to find matching form field
            const field = document.querySelector(`[name="${key}"], #${key}, #edit-${key}, #add-${key}`);
            
            if (field && !field.value) {
                field.value = value;
                field.dispatchEvent(new Event('change'));
                
                // Visual feedback
                field.style.backgroundColor = '#e8f5e8';
                setTimeout(() => {
                    field.style.backgroundColor = '';
                }, 2000);
            }
        });
    }
    
    // ================================================================
    // UTILITY METHODS
    // ================================================================
    
    /**
     * Cache management
     */
    setCache(key, data, timeout = null) {
        this.cache.set(key, {
            data,
            timestamp: Date.now(),
            timeout: timeout || this.cacheTimeout
        });
    }
    
    getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;
        
        if (Date.now() - cached.timestamp > cached.timeout) {
            this.cache.delete(key);
            return null;
        }
        
        return cached.data;
    }
    
    cleanupCache() {
        const now = Date.now();
        for (const [key, cached] of this.cache.entries()) {
            if (now - cached.timestamp > cached.timeout) {
                this.cache.delete(key);
            }
        }
    }
    
    /**
     * Event subscription
     */
    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback);
    }
    
    notifySubscribers(event, data) {
        this.subscribers.forEach(callback => {
            try {
                callback(event, data);
            } catch (error) {
                console.error('AI Integration subscriber error:', error);
            }
        });
    }
    
    /**
     * Extract vehicle data from DOM element
     */
    extractVehicleDataFromElement(element) {
        // Try to extract vehicle data from various sources
        const data = {};
        
        // From data attributes
        Object.keys(element.dataset).forEach(key => {
            if (key.startsWith('vehicle')) {
                const field = key.replace('vehicle', '').toLowerCase();
                data[field] = element.dataset[key];
            }
        });
        
        // From text content (basic extraction)
        const text = element.textContent || '';
        const vinMatch = text.match(/\b[A-HJ-NPR-Z0-9]{17}\b/);
        if (vinMatch) data.vin = vinMatch[0];
        
        return data;
    }
    
    /**
     * Show processing indicator
     */
    showProcessingIndicator(element, message) {
        let indicator = element.parentNode.querySelector('.ai-processing');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'ai-processing';
            indicator.style.cssText = 'color: #007bff; font-size: 12px; margin-top: 5px;';
            element.parentNode.appendChild(indicator);
        }
        indicator.textContent = message;
    }
    
    hideProcessingIndicator(element) {
        const indicator = element.parentNode.querySelector('.ai-processing');
        if (indicator) {
            indicator.remove();
        }
    }
    
    /**
     * Show extraction results
     */
    showExtractionResults(result, input) {
        const container = document.createElement('div');
        container.className = 'extraction-results';
        container.style.cssText = `
            margin-top: 10px;
            padding: 10px;
            background: #e8f5e8;
            border-radius: 4px;
            font-size: 12px;
        `;
        
        container.innerHTML = `
            <strong>✅ Document processed successfully!</strong><br>
            Confidence: ${Math.round((result.confidence || 0) * 100)}%<br>
            Extracted: ${Object.keys(result.extracted_data || {}).length} fields
        `;
        
        input.parentNode.appendChild(container);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (container.parentNode) {
                container.parentNode.removeChild(container);
            }
        }, 5000);
    }
    
    /**
     * Escape HTML for safe insertion
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Get current user context for AI
     */
    getCurrentContext() {
        return {
            user_id: window.currentUser?.id,
            current_page: window.location.pathname,
            timestamp: new Date().toISOString()
        };
    }
}

// Initialize AI integration when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.aiIntegration = new AIIntegration();
});

// Export for use in other modules
window.AIIntegration = AIIntegration;
