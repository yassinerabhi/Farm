// Charts functionality
let currentChart = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts if container exists
    initializeCharts();
    
    // Set up parameter selector for charts
    setupChartControls();
});

function initializeCharts() {
    const chartContainer = document.getElementById('main-chart');
    if (chartContainer) {
        // Default to temperature data for the past day
        fetchChartData('temperature', '1d');
    }
}

function setupChartControls() {
    // Set up parameter selector
    const paramSelector = document.getElementById('param-selector');
    if (paramSelector) {
        paramSelector.addEventListener('change', function() {
            const periodSelector = document.getElementById('period-selector');
            const period = periodSelector ? periodSelector.value : '1d';
            fetchChartData(this.value, period);
        });
    }
    
    // Set up period selector
    const periodSelector = document.getElementById('period-selector');
    if (periodSelector) {
        periodSelector.addEventListener('change', function() {
            const paramSelector = document.getElementById('param-selector');
            const param = paramSelector ? paramSelector.value : 'temperature';
            fetchChartData(param, this.value);
        });
    }
}

function fetchChartData(param, period) {
    // Show loading indicator
    const chartContainer = document.getElementById('chart-container');
    if (chartContainer) {
        chartContainer.innerHTML = '<div class="loader"></div>';
    }
    
    fetch(`/api/chart-data?param=${param}&period=${period}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            createChart(data.labels, data.values, data.param, period);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            if (chartContainer) {
                chartContainer.innerHTML = '<p class="text-danger">Error loading chart data. Please try again.</p>';
            }
        });
}

function createChart(labels, values, param, period) {
    // Get the chart canvas
    const chartContainer = document.getElementById('chart-container');
    
    // Clear previous chart
    if (chartContainer) {
        chartContainer.innerHTML = '<canvas id="main-chart"></canvas>';
    }
    
    const ctx = document.getElementById('main-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (currentChart) {
        currentChart.destroy();
    }
    
    // Get chart configuration based on parameter
    const config = getChartConfig(param, labels, values, period);
    
    // Create new chart
    currentChart = new Chart(ctx, config);
}

function getChartConfig(param, labels, values, period) {
    // Define colors and label based on parameter
    let backgroundColor, borderColor, label, yAxisLabel, icon;
    
    switch(param) {
        case 'moisture':
            backgroundColor = 'rgba(0, 150, 255, 0.2)';
            borderColor = 'rgba(0, 150, 255, 1)';
            label = 'Soil Moisture';
            yAxisLabel = 'Moisture (%)';
            icon = 'fa-tint';
            break;
        case 'temperature':
            backgroundColor = 'rgba(255, 99, 132, 0.2)';
            borderColor = 'rgba(255, 99, 132, 1)';
            label = 'Soil Temperature';
            yAxisLabel = 'Temperature (°C)';
            icon = 'fa-thermometer-half';
            break;
        case 'ph':
            backgroundColor = 'rgba(153, 102, 255, 0.2)';
            borderColor = 'rgba(153, 102, 255, 1)';
            label = 'Soil pH';
            yAxisLabel = 'pH';
            icon = 'fa-flask';
            break;
        case 'ec':
            backgroundColor = 'rgba(255, 159, 64, 0.2)';
            borderColor = 'rgba(255, 159, 64, 1)';
            label = 'Electrical Conductivity';
            yAxisLabel = 'EC (µS/cm)';
            icon = 'fa-bolt';
            break;
        case 'nitrogen':
            backgroundColor = 'rgba(75, 192, 192, 0.2)';
            borderColor = 'rgba(75, 192, 192, 1)';
            label = 'Nitrogen Level';
            yAxisLabel = 'N (mg/kg)';
            icon = 'fa-leaf';
            break;
        case 'phosphorous':
            backgroundColor = 'rgba(255, 206, 86, 0.2)';
            borderColor = 'rgba(255, 206, 86, 1)';
            label = 'Phosphorous Level';
            yAxisLabel = 'P (mg/kg)';
            icon = 'fa-leaf';
            break;
        case 'potassium':
            backgroundColor = 'rgba(54, 162, 235, 0.2)';
            borderColor = 'rgba(54, 162, 235, 1)';
            label = 'Potassium Level';
            yAxisLabel = 'K (mg/kg)';
            icon = 'fa-leaf';
            break;
        case 'bme_temperature':
            backgroundColor = 'rgba(255, 99, 132, 0.2)';
            borderColor = 'rgba(255, 99, 132, 1)';
            label = 'Air Temperature';
            yAxisLabel = 'Temperature (°C)';
            icon = 'fa-thermometer-half';
            break;
        case 'bme_humidity':
            backgroundColor = 'rgba(0, 150, 255, 0.2)';
            borderColor = 'rgba(0, 150, 255, 1)';
            label = 'Air Humidity';
            yAxisLabel = 'Humidity (%)';
            icon = 'fa-tint';
            break;
        case 'bme_pressure':
            backgroundColor = 'rgba(75, 192, 192, 0.2)';
            borderColor = 'rgba(75, 192, 192, 1)';
            label = 'Atmospheric Pressure';
            yAxisLabel = 'Pressure (hPa)';
            icon = 'fa-compress';
            break;
        case 'uv_index':
            backgroundColor = 'rgba(255, 206, 86, 0.2)';
            borderColor = 'rgba(255, 206, 86, 1)';
            label = 'UV Index';
            yAxisLabel = 'UV Index';
            icon = 'fa-sun';
            break;
        case 'rain_level':
            backgroundColor = 'rgba(54, 162, 235, 0.2)';
            borderColor = 'rgba(54, 162, 235, 1)';
            label = 'Rain Level';
            yAxisLabel = 'Rain Level (%)';
            icon = 'fa-cloud-rain';
            break;
        default:
            backgroundColor = 'rgba(201, 203, 207, 0.2)';
            borderColor = 'rgba(201, 203, 207, 1)';
            label = param.replace('_', ' ').charAt(0).toUpperCase() + param.replace('_', ' ').slice(1);
            yAxisLabel = param;
            icon = 'fa-chart-line';
    }
    
    // Update chart title
    const chartTitle = document.getElementById('chart-title');
    if (chartTitle) {
        chartTitle.innerHTML = `<i class="fas ${icon}"></i> ${label}`;
    }
    
    // Define x-axis time unit based on period
    let timeUnit;
    switch(period) {
        case '1d':
            timeUnit = 'hour';
            break;
        case '1w':
            timeUnit = 'day';
            break;
        case '1m':
            timeUnit = 'day';
            break;
        case '1y':
            timeUnit = 'month';
            break;
        default:
            timeUnit = 'hour';
    }
    
    // Return chart configuration
    return {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: values,
                backgroundColor: backgroundColor,
                borderColor: borderColor,
                borderWidth: 2,
                pointRadius: 3,
                pointHoverRadius: 5,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: timeUnit,
                        displayFormats: {
                            hour: 'HH:mm',
                            day: 'MMM D',
                            month: 'MMM YYYY'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: yAxisLabel
                    }
                }
            }
        }
    };
}
