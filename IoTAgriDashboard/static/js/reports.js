// Reports functionality
document.addEventListener('DOMContentLoaded', function() {
    // Set up report generation form
    setupReportForm();
    
    // Initialize date pickers
    initializeDatePickers();
});

function setupReportForm() {
    const reportForm = document.getElementById('report-form');
    
    if (reportForm) {
        reportForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            // Validate form
            if (!validateReportForm()) {
                return;
            }
            
            // Show loading spinner
            const submitButton = reportForm.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
            submitButton.disabled = true;
            
            // Get form data
            const title = document.getElementById('report-title').value;
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            
            // Send request to generate report
            generateReport(title, startDate, endDate)
                .then(data => {
                    // Reset form
                    reportForm.reset();
                    
                    // Show success message
                    showAlert('Report generated successfully!', 'success');
                    
                    // Reset button
                    submitButton.innerHTML = originalButtonText;
                    submitButton.disabled = false;
                    
                    // Refresh reports list
                    refreshReportsList();
                })
                .catch(error => {
                    console.error('Error generating report:', error);
                    
                    // Show error message
                    showAlert('Error generating report. Please try again.', 'danger');
                    
                    // Reset button
                    submitButton.innerHTML = originalButtonText;
                    submitButton.disabled = false;
                });
        });
    }
}

function validateReportForm() {
    const title = document.getElementById('report-title').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    // Check if title is provided
    if (!title) {
        showAlert('Please enter a report title.', 'warning');
        return false;
    }
    
    // Check if dates are provided
    if (!startDate || !endDate) {
        showAlert('Please select both start and end dates.', 'warning');
        return false;
    }
    
    // Check if start date is before end date
    if (new Date(startDate) > new Date(endDate)) {
        showAlert('Start date must be before end date.', 'warning');
        return false;
    }
    
    // Check if date range is not too large
    const dateRange = (new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24);
    if (dateRange > 365) {
        showAlert('Date range cannot exceed 1 year.', 'warning');
        return false;
    }
    
    return true;
}

function generateReport(title, startDate, endDate) {
    return fetch('/api/generate-report', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: title,
            start_date: startDate,
            end_date: endDate
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    });
}

function refreshReportsList() {
    // In a real implementation, this would fetch the latest reports
    // For simplicity, we'll just reload the page
    window.location.reload();
}

function initializeDatePickers() {
    // This function would initialize date pickers
    // Implementation depends on the date picker library used
    // For this demo, we're using native HTML date inputs
    
    // Set default dates (last 7 days)
    const endDateInput = document.getElementById('end-date');
    const startDateInput = document.getElementById('start-date');
    
    if (endDateInput && startDateInput) {
        const today = new Date();
        const lastWeek = new Date();
        lastWeek.setDate(today.getDate() - 7);
        
        // Format dates as YYYY-MM-DD
        endDateInput.value = formatDate(today);
        startDateInput.value = formatDate(lastWeek);
        
        // Set max date for both inputs to today
        endDateInput.max = formatDate(today);
        startDateInput.max = formatDate(today);
    }
}

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

function showAlert(message, type) {
    const alertsContainer = document.getElementById('alerts-container');
    
    if (alertsContainer) {
        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.role = 'alert';
        
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Add to container
        alertsContainer.appendChild(alert);
        
        // Remove after 5 seconds
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    }
}
