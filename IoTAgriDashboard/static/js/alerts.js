// Alerts functionality
document.addEventListener('DOMContentLoaded', function() {
    // Setup alert acknowledgment
    setupAlertAcknowledgment();
    
    // Setup alert refresh
    setupAlertRefresh();
});

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
        // Remove the alert from the UI with a fade out effect
        const alertElement = document.querySelector(`.alert-item[data-alert-id="${alertId}"]`);
        if (alertElement) {
            alertElement.style.transition = 'opacity 0.5s ease';
            alertElement.style.opacity = 0;
            
            setTimeout(() => {
                alertElement.remove();
                
                // Check if there are no more alerts
                const alertsContainer = document.querySelector('.alerts-container');
                if (alertsContainer && alertsContainer.children.length === 0) {
                    alertsContainer.innerHTML = '<p class="text-muted">No active alerts.</p>';
                }
            }, 500);
        }
    })
    .catch(error => {
        console.error('Error acknowledging alert:', error);
    });
}

function setupAlertRefresh() {
    // Refresh alerts every 5 minutes
    setInterval(refreshAlerts, 5 * 60 * 1000);
}

function refreshAlerts() {
    // This function would fetch the latest alerts from the server
    // In a real implementation, you'd have an API endpoint for this
    // For now, we'll just reload the alerts container
    const alertsContainer = document.querySelector('.alerts-container');
    if (alertsContainer) {
        // You could implement an AJAX call here to refresh just the alerts
        // For simplicity, we're not implementing this in the demo
    }
}

// Show notifications for alerts
function showAlertNotification(message, level) {
    // Check if browser supports notifications
    if (!("Notification" in window)) {
        console.log("This browser does not support desktop notifications");
        return;
    }
    
    // Check if permission is already granted
    if (Notification.permission === "granted") {
        createNotification(message, level);
    }
    // Otherwise, ask for permission
    else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                createNotification(message, level);
            }
        });
    }
}

function createNotification(message, level) {
    // Create notification
    const notification = new Notification("AgriIoT Alert", {
        body: message,
        icon: level === 'danger' ? '/static/img/alert-critical.svg' : '/static/img/alert-warning.svg'
    });
    
    // Close the notification after 5 seconds
    setTimeout(notification.close.bind(notification), 5000);
    
    // Add click event
    notification.onclick = function() {
        window.focus();
        this.close();
    };
}
