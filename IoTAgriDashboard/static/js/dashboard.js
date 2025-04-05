// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard data refresh
    initializeDashboard();
    
    // Initialize charts
    initializeCharts();
    
    // Set up alert acknowledgment
    setupAlertAcknowledgment();
    
    // Update battery indicators
    updateBatteryIndicators();
});

function initializeDashboard() {
    // Fetch initial data
    fetchLatestData();
    
    // Set up refresh interval (every 60 seconds)
    setInterval(fetchLatestData, 60000);
}

function fetchLatestData() {
    fetch('/api/recent-data')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateDashboardWidgets(data);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

function updateDashboardWidgets(data) {
    // Update sensor values in the dashboard
    updateWidgetValue('moisture', data.moisture, '%');
    updateWidgetValue('temperature', data.temperature, '°C');
    updateWidgetValue('ph', data.ph, '');
    updateWidgetValue('ec', data.ec, 'µS/cm');
    updateWidgetValue('nitrogen', data.nitrogen, 'mg/kg');
    updateWidgetValue('phosphorous', data.phosphorous, 'mg/kg');
    updateWidgetValue('potassium', data.potassium, 'mg/kg');
    updateWidgetValue('salinity', data.salinity, 'ppt');
    
    // Update environmental sensors
    updateWidgetValue('bme-temperature', data.bme_temperature, '°C');
    updateWidgetValue('bme-humidity', data.bme_humidity, '%');
    updateWidgetValue('bme-pressure', data.bme_pressure, 'hPa');
    updateWidgetValue('bme-gas', data.bme_gas, 'KOhm');
    updateWidgetValue('uv-index', data.uv_index, '');
    
    // Update rain level if available
    if (data.rain_level !== null && data.rain_level !== undefined) {
        updateWidgetValue('rain-level', data.rain_level, '%');
        
        // Update rain status message
        const rainStatus = document.getElementById('rain-status');
        if (rainStatus) {
            if (data.rain_level < 30) {
                rainStatus.textContent = 'Heavy rain detected';
                rainStatus.className = 'text-danger';
            } else if (data.rain_level < 70) {
                rainStatus.textContent = 'Light rain detected';
                rainStatus.className = 'text-warning';
            } else {
                rainStatus.textContent = 'No rain detected';
                rainStatus.className = 'text-success';
            }
        }
    }
    
    // Update battery information
    if (data.battery_percentage !== null && data.battery_percentage !== undefined) {
        updateBatteryWidget(data.battery_percentage, data.battery_voltage);
    }
    
    // Update last updated timestamp
    const lastUpdated = document.getElementById('last-updated');
    if (lastUpdated) {
        const date = new Date(data.timestamp);
        lastUpdated.textContent = date.toLocaleString();
    }
}

function updateWidgetValue(id, value, unit) {
    const valueElement = document.getElementById(`${id}-value`);
    if (valueElement && value !== null && value !== undefined) {
        // Format number based on type
        let formattedValue;
        if (Number.isInteger(value)) {
            formattedValue = value;
        } else {
            formattedValue = parseFloat(value).toFixed(1);
        }
        
        valueElement.textContent = `${formattedValue}${unit}`;
    }
}

function updateBatteryWidget(percentage, voltage) {
    const batteryPercentage = document.getElementById('battery-percentage');
    const batteryVoltage = document.getElementById('battery-voltage');
    const batteryLevel = document.getElementById('battery-level');
    
    if (batteryPercentage) {
        batteryPercentage.textContent = `${percentage}%`;
    }
    
    if (batteryVoltage) {
        batteryVoltage.textContent = `${voltage.toFixed(2)}V`;
    }
    
    if (batteryLevel) {
        batteryLevel.style.width = `${percentage}%`;
        
        // Update color based on level
        if (percentage < 10) {
            batteryLevel.className = 'battery-level battery-critical';
        } else if (percentage < 20) {
            batteryLevel.className = 'battery-level battery-low';
        } else {
            batteryLevel.className = 'battery-level';
        }
    }
}

function updateBatteryIndicators() {
    // Find all battery indicators on the page
    const batteryIndicators = document.querySelectorAll('.battery-indicator');
    
    batteryIndicators.forEach(indicator => {
        const percentage = parseInt(indicator.getAttribute('data-percentage'), 10);
        const level = indicator.querySelector('.battery-level');
        
        if (level) {
            level.style.width = `${percentage}%`;
            
            // Update color based on level
            if (percentage < 10) {
                level.className = 'battery-level battery-critical';
            } else if (percentage < 20) {
                level.className = 'battery-level battery-low';
            } else {
                level.className = 'battery-level';
            }
        }
    });
}

function setupAlertAcknowledgment() {
    // Add event listeners to alert acknowledgment buttons
    document.querySelectorAll('.acknowledge-alert').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const alertId = this.getAttribute('data-alert-id');
            acknowledgeAlert(alertId);
        });
    });
}

function acknowledgeAlert(alertId) {
    fetch(`/api/acknowledge-alert/${alertId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Remove the alert from the UI
        const alertElement = document.querySelector(`.alert-item[data-alert-id="${alertId}"]`);
        if (alertElement) {
            alertElement.remove();
        }
    })
    .catch(error => {
        console.error('Error acknowledging alert:', error);
    });
}
