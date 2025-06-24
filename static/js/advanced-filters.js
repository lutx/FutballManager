/**
 * Advanced Filters System for Football Manager
 * Provides powerful filtering capabilities with real-time updates
 */

class AdvancedFilters {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            endpoint: '/api/filtered-data',
            debounceTime: 300,
            savePresets: true,
            realTimeSearch: true,
            ...options
        };
        
        this.filters = new Map();
        this.presets = new Map();
        this.debounceTimer = null;
        this.currentData = [];
        
        this.init();
    }

    init() {
        if (!this.container) {
            console.error('Filter container not found');
            return;
        }
        
        this.createFilterInterface();
        this.bindEvents();
        this.loadSavedPresets();
        this.loadInitialData();
    }

    createFilterInterface() {
        const html = `
            <div class="advanced-filters-panel">
                <div class="filter-header">
                    <h5 class="filter-title">
                        <i class="bi bi-funnel me-2"></i>Advanced Filters
                    </h5>
                    <div class="filter-actions">
                        <button class="btn btn-sm btn-outline-primary" id="save-preset-btn">
                            <i class="bi bi-bookmark me-1"></i>Save Preset
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" id="clear-all-btn">
                            <i class="bi bi-x-circle me-1"></i>Clear All
                        </button>
                    </div>
                </div>

                <div class="filter-body">
                    <!-- Search Filter -->
                    <div class="filter-group">
                        <label class="filter-label">
                            <i class="bi bi-search me-2"></i>Search
                        </label>
                        <div class="search-input-wrapper">
                            <input type="text" 
                                   class="form-control" 
                                   id="search-input"
                                   placeholder="Search teams, tournaments, matches...">
                            <div class="search-suggestions" id="search-suggestions"></div>
                        </div>
                    </div>

                    <!-- Teams Multi-Select -->
                    <div class="filter-group">
                        <label class="filter-label">
                            <i class="bi bi-people me-2"></i>Teams
                        </label>
                        <div class="multi-select-wrapper">
                            <div class="multi-select" id="teams-filter">
                                <div class="selected-display">
                                    <span class="placeholder">Select teams...</span>
                                    <i class="bi bi-chevron-down"></i>
                                </div>
                                <div class="dropdown-content">
                                    <div class="dropdown-search">
                                        <input type="text" placeholder="Search teams..." class="form-control form-control-sm">
                                    </div>
                                    <div class="dropdown-options"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Date Range Filter -->
                    <div class="filter-group">
                        <label class="filter-label">
                            <i class="bi bi-calendar-range me-2"></i>Date Range
                        </label>
                        <div class="date-range-wrapper">
                            <input type="date" class="form-control" id="date-from" placeholder="From">
                            <span class="date-separator">to</span>
                            <input type="date" class="form-control" id="date-to" placeholder="To">
                            <div class="date-presets">
                                <button class="btn btn-sm btn-outline-secondary" data-preset="today">Today</button>
                                <button class="btn btn-sm btn-outline-secondary" data-preset="week">This Week</button>
                                <button class="btn btn-sm btn-outline-secondary" data-preset="month">This Month</button>
                            </div>
                        </div>
                    </div>

                    <!-- Status Filter -->
                    <div class="filter-group">
                        <label class="filter-label">
                            <i class="bi bi-flag me-2"></i>Status
                        </label>
                        <div class="checkbox-group">
                            <label class="checkbox-item">
                                <input type="checkbox" value="upcoming" data-filter="status">
                                <span class="checkmark"></span>
                                <span class="status-badge badge-warning">Upcoming</span>
                            </label>
                            <label class="checkbox-item">
                                <input type="checkbox" value="ongoing" data-filter="status">
                                <span class="checkmark"></span>
                                <span class="status-badge badge-info">Ongoing</span>
                            </label>
                            <label class="checkbox-item">
                                <input type="checkbox" value="completed" data-filter="status">
                                <span class="checkmark"></span>
                                <span class="status-badge badge-success">Completed</span>
                            </label>
                        </div>
                    </div>

                    <!-- Tournament Type Filter -->
                    <div class="filter-group">
                        <label class="filter-label">
                            <i class="bi bi-trophy me-2"></i>Tournament Type
                        </label>
                        <select class="form-select" id="tournament-type-filter" multiple>
                            <option value="league">League</option>
                            <option value="cup">Cup</option>
                            <option value="friendly">Friendly</option>
                            <option value="playoff">Playoff</option>
                        </select>
                    </div>

                    <!-- Score Range Filter -->
                    <div class="filter-group">
                        <label class="filter-label">
                            <i class="bi bi-bar-chart me-2"></i>Score Range
                        </label>
                        <div class="range-slider-wrapper">
                            <div class="range-slider">
                                <input type="range" min="0" max="10" value="0" class="range-input" id="score-min">
                                <input type="range" min="0" max="10" value="10" class="range-input" id="score-max">
                            </div>
                            <div class="range-values">
                                <span>Min: <span id="score-min-value">0</span></span>
                                <span>Max: <span id="score-max-value">10</span></span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Saved Presets -->
                <div class="filter-presets" id="filter-presets">
                    <h6>Saved Presets</h6>
                    <div class="preset-buttons"></div>
                </div>

                <!-- Filter Summary -->
                <div class="filter-summary">
                    <div class="active-filters" id="active-filters"></div>
                    <div class="results-count">
                        Showing <span id="results-count">0</span> results
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }

    bindEvents() {
        // Real-time search
        const searchInput = document.getElementById('search-input');
        searchInput?.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });

        // Multi-select teams
        this.initializeMultiSelect();

        // Date range filters
        document.getElementById('date-from')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('date-to')?.addEventListener('change', () => this.applyFilters());

        // Date presets
        document.querySelectorAll('[data-preset]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.applyDatePreset(e.target.dataset.preset);
            });
        });

        // Status checkboxes
        document.querySelectorAll('input[data-filter="status"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.applyFilters());
        });

        // Tournament type
        document.getElementById('tournament-type-filter')?.addEventListener('change', () => this.applyFilters());

        // Score range sliders
        document.getElementById('score-min')?.addEventListener('input', (e) => {
            document.getElementById('score-min-value').textContent = e.target.value;
            this.applyFilters();
        });

        document.getElementById('score-max')?.addEventListener('input', (e) => {
            document.getElementById('score-max-value').textContent = e.target.value;
            this.applyFilters();
        });

        // Control buttons
        document.getElementById('save-preset-btn')?.addEventListener('click', () => this.showSavePresetDialog());
        document.getElementById('clear-all-btn')?.addEventListener('click', () => this.clearAllFilters());
    }

    initializeMultiSelect() {
        const multiSelect = document.getElementById('teams-filter');
        const selectedDisplay = multiSelect?.querySelector('.selected-display');
        const dropdownContent = multiSelect?.querySelector('.dropdown-content');
        
        // Toggle dropdown
        selectedDisplay?.addEventListener('click', () => {
            dropdownContent?.classList.toggle('show');
        });

        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            if (!multiSelect?.contains(e.target)) {
                dropdownContent?.classList.remove('show');
            }
        });

        // Load team options
        this.loadTeamOptions();
    }

    async loadTeamOptions() {
        try {
            const response = await fetch('/api/teams');
            const teams = await response.json();
            
            const optionsContainer = document.querySelector('#teams-filter .dropdown-options');
            if (!optionsContainer) return;

            optionsContainer.innerHTML = teams.map(team => `
                <label class="dropdown-option">
                    <input type="checkbox" value="${team.id}" data-team-name="${team.name}">
                    <span class="option-text">${team.name}</span>
                </label>
            `).join('');

            // Bind checkbox events
            optionsContainer.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    this.updateSelectedTeams();
                    this.applyFilters();
                });
            });

        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    updateSelectedTeams() {
        const selectedCheckboxes = document.querySelectorAll('#teams-filter input[type="checkbox"]:checked');
        const selectedDisplay = document.querySelector('#teams-filter .selected-display span');
        
        if (selectedCheckboxes.length === 0) {
            selectedDisplay.textContent = 'Select teams...';
            selectedDisplay.className = 'placeholder';
        } else if (selectedCheckboxes.length === 1) {
            selectedDisplay.textContent = selectedCheckboxes[0].dataset.teamName;
            selectedDisplay.className = 'selected-text';
        } else {
            selectedDisplay.textContent = `${selectedCheckboxes.length} teams selected`;
            selectedDisplay.className = 'selected-text';
        }
    }

    handleSearch(query) {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        this.debounceTimer = setTimeout(() => {
            this.filters.set('search', query);
            this.applyFilters();
            
            if (query.length > 2) {
                this.showSearchSuggestions(query);
            } else {
                this.hideSearchSuggestions();
            }
        }, this.options.debounceTime);
    }

    async showSearchSuggestions(query) {
        try {
            const response = await fetch(`/api/search-suggestions?q=${encodeURIComponent(query)}`);
            const suggestions = await response.json();
            
            const suggestionsContainer = document.getElementById('search-suggestions');
            if (!suggestionsContainer) return;

            suggestionsContainer.innerHTML = suggestions.map(item => `
                <div class="suggestion-item" data-type="${item.type}" data-id="${item.id}">
                    <i class="bi bi-${this.getSuggestionIcon(item.type)} me-2"></i>
                    <span>${item.name}</span>
                    <small class="text-muted">${item.type}</small>
                </div>
            `).join('');

            suggestionsContainer.style.display = suggestions.length > 0 ? 'block' : 'none';

            // Bind suggestion click events
            suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
                item.addEventListener('click', () => {
                    this.applySuggestion(item.dataset.type, item.dataset.id, item.textContent.trim());
                });
            });

        } catch (error) {
            console.error('Failed to load search suggestions:', error);
        }
    }

    hideSearchSuggestions() {
        const suggestionsContainer = document.getElementById('search-suggestions');
        if (suggestionsContainer) {
            suggestionsContainer.style.display = 'none';
        }
    }

    getSuggestionIcon(type) {
        const icons = {
            team: 'people',
            tournament: 'trophy',
            match: 'calendar-event'
        };
        return icons[type] || 'search';
    }

    applySuggestion(type, id, name) {
        // Apply the suggestion as a filter
        if (type === 'team') {
            const checkbox = document.querySelector(`#teams-filter input[value="${id}"]`);
            if (checkbox) {
                checkbox.checked = true;
                this.updateSelectedTeams();
            }
        }
        
        this.hideSearchSuggestions();
        this.applyFilters();
    }

    applyDatePreset(preset) {
        const today = new Date();
        const dateFrom = document.getElementById('date-from');
        const dateTo = document.getElementById('date-to');
        
        let fromDate, toDate;
        
        switch (preset) {
            case 'today':
                fromDate = toDate = today.toISOString().split('T')[0];
                break;
            case 'week':
                const weekStart = new Date(today.setDate(today.getDate() - today.getDay()));
                const weekEnd = new Date(today.setDate(today.getDate() - today.getDay() + 6));
                fromDate = weekStart.toISOString().split('T')[0];
                toDate = weekEnd.toISOString().split('T')[0];
                break;
            case 'month':
                const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
                const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                fromDate = monthStart.toISOString().split('T')[0];
                toDate = monthEnd.toISOString().split('T')[0];
                break;
        }
        
        if (dateFrom) dateFrom.value = fromDate;
        if (dateTo) dateTo.value = toDate;
        
        this.applyFilters();
    }

    async applyFilters() {
        const filterData = this.collectFilterData();
        this.updateActiveFiltersDisplay(filterData);
        
        try {
            const response = await fetch(this.options.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.FOOTBALL_APP?.csrfToken || ''
                },
                body: JSON.stringify(filterData)
            });

            if (!response.ok) throw new Error('Filter request failed');
            
            const result = await response.json();
            this.currentData = result.data || [];
            
            // Update results count
            const resultsCount = document.getElementById('results-count');
            if (resultsCount) {
                resultsCount.textContent = this.currentData.length;
            }
            
            // Emit event for other components to listen
            document.dispatchEvent(new CustomEvent('filtersApplied', {
                detail: { data: this.currentData, filters: filterData }
            }));
            
        } catch (error) {
            console.error('Filter application failed:', error);
        }
    }

    collectFilterData() {
        const data = {};
        
        // Search
        const search = document.getElementById('search-input')?.value;
        if (search) data.search = search;
        
        // Teams
        const selectedTeams = Array.from(document.querySelectorAll('#teams-filter input:checked')).map(cb => cb.value);
        if (selectedTeams.length > 0) data.teams = selectedTeams;
        
        // Date range
        const dateFrom = document.getElementById('date-from')?.value;
        const dateTo = document.getElementById('date-to')?.value;
        if (dateFrom) data.date_from = dateFrom;
        if (dateTo) data.date_to = dateTo;
        
        // Status
        const selectedStatuses = Array.from(document.querySelectorAll('input[data-filter="status"]:checked')).map(cb => cb.value);
        if (selectedStatuses.length > 0) data.status = selectedStatuses;
        
        // Tournament type
        const tournamentType = document.getElementById('tournament-type-filter')?.selectedOptions;
        if (tournamentType && tournamentType.length > 0) {
            data.tournament_type = Array.from(tournamentType).map(option => option.value);
        }
        
        // Score range
        const scoreMin = document.getElementById('score-min')?.value;
        const scoreMax = document.getElementById('score-max')?.value;
        if (scoreMin) data.score_min = parseInt(scoreMin);
        if (scoreMax) data.score_max = parseInt(scoreMax);
        
        return data;
    }

    updateActiveFiltersDisplay(filterData) {
        const container = document.getElementById('active-filters');
        if (!container) return;
        
        const filterTags = [];
        
        // Create filter tags
        Object.entries(filterData).forEach(([key, value]) => {
            if (Array.isArray(value) && value.length > 0) {
                filterTags.push(`
                    <span class="filter-tag" data-filter="${key}">
                        ${this.getFilterLabel(key)}: ${value.length} selected
                        <i class="bi bi-x" onclick="this.removeFilter('${key}')"></i>
                    </span>
                `);
            } else if (value) {
                filterTags.push(`
                    <span class="filter-tag" data-filter="${key}">
                        ${this.getFilterLabel(key)}: ${value}
                        <i class="bi bi-x" onclick="this.removeFilter('${key}')"></i>
                    </span>
                `);
            }
        });
        
        container.innerHTML = filterTags.join('');
    }

    getFilterLabel(key) {
        const labels = {
            search: 'Search',
            teams: 'Teams',
            date_from: 'From',
            date_to: 'To',
            status: 'Status',
            tournament_type: 'Type',
            score_min: 'Min Score',
            score_max: 'Max Score'
        };
        return labels[key] || key;
    }

    clearAllFilters() {
        // Clear all form inputs
        document.getElementById('search-input').value = '';
        document.getElementById('date-from').value = '';
        document.getElementById('date-to').value = '';
        
        // Uncheck all checkboxes
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        
        // Reset selects
        document.querySelectorAll('select').forEach(select => {
            select.selectedIndex = -1;
        });
        
        // Reset range sliders
        document.getElementById('score-min').value = 0;
        document.getElementById('score-max').value = 10;
        document.getElementById('score-min-value').textContent = '0';
        document.getElementById('score-max-value').textContent = '10';
        
        // Update team selection display
        this.updateSelectedTeams();
        
        // Apply empty filters
        this.applyFilters();
    }

    async loadInitialData() {
        await this.applyFilters();
    }

    // Save/Load Presets
    showSavePresetDialog() {
        const name = prompt('Enter preset name:');
        if (name) {
            this.savePreset(name, this.collectFilterData());
        }
    }

    savePreset(name, filterData) {
        this.presets.set(name, filterData);
        
        if (this.options.savePresets) {
            localStorage.setItem('football-filter-presets', JSON.stringify(Array.from(this.presets.entries())));
        }
        
        this.updatePresetButtons();
    }

    loadSavedPresets() {
        if (this.options.savePresets) {
            const saved = localStorage.getItem('football-filter-presets');
            if (saved) {
                this.presets = new Map(JSON.parse(saved));
                this.updatePresetButtons();
            }
        }
    }

    updatePresetButtons() {
        const container = document.querySelector('.preset-buttons');
        if (!container) return;
        
        container.innerHTML = Array.from(this.presets.entries()).map(([name, filters]) => `
            <button class="btn btn-sm btn-outline-info preset-btn" data-preset="${name}">
                ${name}
                <i class="bi bi-x-circle ms-1" data-action="delete"></i>
            </button>
        `).join('');
        
        // Bind preset button events
        container.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (e.target.dataset.action === 'delete') {
                    e.stopPropagation();
                    this.deletePreset(btn.dataset.preset);
                } else {
                    this.loadPreset(btn.dataset.preset);
                }
            });
        });
    }

    loadPreset(name) {
        const filterData = this.presets.get(name);
        if (!filterData) return;
        
        // Apply preset data to form
        Object.entries(filterData).forEach(([key, value]) => {
            // Implementation specific to each filter type
            // This would need to be expanded based on the specific filters
        });
        
        this.applyFilters();
    }

    deletePreset(name) {
        if (confirm(`Delete preset "${name}"?`)) {
            this.presets.delete(name);
            this.updatePresetButtons();
            
            if (this.options.savePresets) {
                localStorage.setItem('football-filter-presets', JSON.stringify(Array.from(this.presets.entries())));
            }
        }
    }
}

// Auto-initialize filters on page load
document.addEventListener('DOMContentLoaded', () => {
    const filterContainer = document.getElementById('advanced-filters');
    if (filterContainer) {
        window.advancedFilters = new AdvancedFilters('advanced-filters');
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdvancedFilters;
}