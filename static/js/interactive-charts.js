/**
 * Interactive Charts System for Football Manager
 * Provides dynamic, responsive charts with real-time updates
 */

class FootballCharts {
    constructor() {
        this.charts = new Map();
        this.colors = {
            primary: '#4f46e5',
            success: '#059669',
            warning: '#d97706', 
            danger: '#dc2626',
            info: '#0284c7',
            secondary: '#64748b'
        };
        this.init();
    }

    init() {
        // Auto-initialize charts on page load
        this.initializeChartsOnPage();
        this.setupChartUpdates();
    }

    initializeChartsOnPage() {
        // Find all chart containers and initialize them
        const chartContainers = document.querySelectorAll('[data-chart-type]');
        chartContainers.forEach(container => {
            const chartType = container.dataset.chartType;
            const chartData = JSON.parse(container.dataset.chartData || '{}');
            this.createChart(container.id, chartType, chartData);
        });
    }

    createChart(containerId, type, data) {
        const container = document.getElementById(containerId);
        if (!container) return;

        switch (type) {
            case 'tournament-progress':
                return this.createTournamentProgressChart(containerId, data);
            case 'team-performance':
                return this.createTeamPerformanceChart(containerId, data);
            case 'match-activity':
                return this.createMatchActivityHeatmap(containerId, data);
            case 'score-distribution':
                return this.createScoreDistributionChart(containerId, data);
            case 'season-overview':
                return this.createSeasonOverviewChart(containerId, data);
            default:
                console.warn(`Unknown chart type: ${type}`);
        }
    }

    // Tournament Progress Chart - Shows matches completed over time
    createTournamentProgressChart(containerId, data) {
        const ctx = document.getElementById(containerId);
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates || [],
                datasets: [{
                    label: 'Matches Completed',
                    data: data.completed || [],
                    borderColor: this.colors.success,
                    backgroundColor: this.colors.success + '20',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Matches Scheduled',
                    data: data.scheduled || [],
                    borderColor: this.colors.primary,
                    backgroundColor: this.colors.primary + '20',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Tournament Progress',
                        font: { size: 16, weight: 'bold' }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        callbacks: {
                            title: (context) => `Date: ${context[0].label}`,
                            label: (context) => `${context.dataset.label}: ${context.parsed.y} matches`
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: { usePointStyle: true }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    // Team Performance Comparison Chart
    createTeamPerformanceChart(containerId, data) {
        const ctx = document.getElementById(containerId);
        const chart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Wins', 'Draws', 'Losses', 'Goals Scored', 'Goals Against', 'Clean Sheets'],
                datasets: data.teams?.map((team, index) => ({
                    label: team.name,
                    data: [
                        team.wins || 0,
                        team.draws || 0, 
                        team.losses || 0,
                        team.goals_scored || 0,
                        team.goals_against || 0,
                        team.clean_sheets || 0
                    ],
                    borderColor: this.getTeamColor(index),
                    backgroundColor: this.getTeamColor(index) + '30',
                    pointBackgroundColor: this.getTeamColor(index),
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: this.getTeamColor(index)
                })) || []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Team Performance Comparison',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: Math.max(...data.teams?.flatMap(team => [
                            team.wins, team.draws, team.losses, 
                            team.goals_scored, team.goals_against, team.clean_sheets
                        ]) || [10])
                    }
                }
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    // Match Activity Heatmap - Shows when matches are most active
    createMatchActivityHeatmap(containerId, data) {
        const container = document.getElementById(containerId);
        
        const options = {
            series: data.series || [],
            chart: {
                height: 350,
                type: 'heatmap',
                animations: {
                    enabled: true,
                    speed: 800,
                    animateGradually: { enabled: true, delay: 150 }
                },
                toolbar: { show: false }
            },
            dataLabels: { 
                enabled: false 
            },
            colors: [this.colors.success],
            title: {
                text: 'Match Activity Heatmap',
                align: 'center',
                style: { fontSize: '16px', fontWeight: 'bold' }
            },
            xaxis: {
                categories: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            },
            yaxis: {
                categories: ['Morning', 'Afternoon', 'Evening', 'Night']
            },
            tooltip: {
                custom: function({ series, seriesIndex, dataPointIndex, w }) {
                    const value = series[seriesIndex][dataPointIndex];
                    const day = w.globals.categoryLabels[dataPointIndex];
                    const time = w.config.yaxis[0].categories[seriesIndex];
                    return `<div class="custom-tooltip">
                        <strong>${day} ${time}</strong><br>
                        ${value} matches
                    </div>`;
                }
            }
        };

        const chart = new ApexCharts(container, options);
        chart.render();
        this.charts.set(containerId, chart);
        return chart;
    }

    // Score Distribution Chart - Shows common score patterns
    createScoreDistributionChart(containerId, data) {
        const ctx = document.getElementById(containerId);
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels || ['0-0', '1-0', '1-1', '2-0', '2-1', '2-2', 'Other'],
                datasets: [{
                    data: data.values || [5, 15, 20, 12, 18, 8, 22],
                    backgroundColor: [
                        this.colors.secondary,
                        this.colors.success,
                        this.colors.warning,
                        this.colors.primary,
                        this.colors.info,
                        this.colors.danger,
                        '#94a3b8'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Most Common Score Results',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'right',
                        labels: { usePointStyle: true }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const percentage = ((context.parsed / context.dataset.data.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                                return `${context.label}: ${context.parsed} matches (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    // Season Overview Chart - Multi-metric dashboard
    createSeasonOverviewChart(containerId, data) {
        const ctx = document.getElementById(containerId);
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.months || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Matches Played',
                    data: data.matches || [],
                    backgroundColor: this.colors.primary + '80',
                    borderColor: this.colors.primary,
                    borderWidth: 1,
                    yAxisID: 'y'
                }, {
                    label: 'Goals Scored',
                    data: data.goals || [],
                    type: 'line',
                    borderColor: this.colors.success,
                    backgroundColor: this.colors.success + '20',
                    fill: false,
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Season Overview',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Matches' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Goals' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    // Utility Methods
    getTeamColor(index) {
        const colorArray = [
            this.colors.primary,
            this.colors.success,
            this.colors.warning,
            this.colors.danger,
            this.colors.info,
            this.colors.secondary
        ];
        return colorArray[index % colorArray.length];
    }

    // Real-time Update Methods
    updateChartData(containerId, newData) {
        const chart = this.charts.get(containerId);
        if (!chart) return;

        chart.data = newData;
        chart.update('active');
    }

    addDataPoint(containerId, label, data) {
        const chart = this.charts.get(containerId);
        if (!chart) return;

        chart.data.labels.push(label);
        chart.data.datasets.forEach((dataset, index) => {
            dataset.data.push(data[index] || 0);
        });
        chart.update('active');
    }

    // Setup automatic updates via WebSocket
    setupChartUpdates() {
        if (window.socket) {
            window.socket.on('chart_update', (data) => {
                this.updateChartData(data.chartId, data.newData);
            });

            window.socket.on('chart_add_point', (data) => {
                this.addDataPoint(data.chartId, data.label, data.data);
            });
        }
    }

    // Destroy chart (cleanup)
    destroyChart(containerId) {
        const chart = this.charts.get(containerId);
        if (chart) {
            chart.destroy();
            this.charts.delete(containerId);
        }
    }

    // Resize all charts (for responsive behavior)
    resizeCharts() {
        this.charts.forEach(chart => {
            chart.resize();
        });
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.footballCharts = new FootballCharts();
});

// Handle window resize
window.addEventListener('resize', () => {
    if (window.footballCharts) {
        window.footballCharts.resizeCharts();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FootballCharts;
}