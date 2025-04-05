// Weather functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize weather icons
    updateWeatherIcons();
    
    // Setup refresh button
    const refreshButton = document.getElementById('refresh-weather');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshWeatherData);
    }
    
    // Setup fetch weather button if present (for when no data is available)
    const fetchWeatherButton = document.getElementById('fetch-weather');
    if (fetchWeatherButton) {
        fetchWeatherButton.addEventListener('click', refreshWeatherData);
    }
});

function updateWeatherIcons() {
    // Get the weather condition
    const weatherMain = document.getElementById('weather-main');
    const weatherIcon = document.getElementById('weather-icon');
    
    if (weatherMain && weatherIcon) {
        const weatherCondition = weatherMain.textContent.trim().toLowerCase();
        let iconClass = 'fa-cloud';
        
        // Map weather conditions to Font Awesome icons
        switch (weatherCondition) {
            case 'clear':
            case 'clear sky':
                iconClass = 'fa-sun';
                break;
            case 'few clouds':
            case 'scattered clouds':
                iconClass = 'fa-cloud-sun';
                break;
            case 'broken clouds':
            case 'clouds':
            case 'overcast clouds':
                iconClass = 'fa-cloud';
                break;
            case 'shower rain':
            case 'rain':
            case 'light rain':
            case 'moderate rain':
                iconClass = 'fa-cloud-rain';
                break;
            case 'thunderstorm':
                iconClass = 'fa-bolt';
                break;
            case 'snow':
                iconClass = 'fa-snowflake';
                break;
            case 'mist':
            case 'fog':
            case 'haze':
                iconClass = 'fa-smog';
                break;
            default:
                iconClass = 'fa-cloud';
        }
        
        // Update icon
        weatherIcon.className = `fas ${iconClass} weather-icon`;
    }
    
    // Update wind direction icon
    const windDirection = document.getElementById('wind-direction');
    const windDirectionIcon = document.getElementById('wind-direction-icon');
    
    if (windDirection && windDirectionIcon) {
        const direction = parseInt(windDirection.getAttribute('data-direction'), 10);
        
        // Rotate the arrow to point in the wind direction
        // Wind direction is where the wind is coming FROM, so we add 180 degrees
        windDirectionIcon.style.transform = `rotate(${direction + 180}deg)`;
    }
}

// Function to refresh weather data
function refreshWeatherData() {
    // Show loading indicator
    const weatherContainer = document.getElementById('weather-container');
    
    if (weatherContainer) {
        const loader = document.createElement('div');
        loader.className = 'loader';
        weatherContainer.appendChild(loader);
        
        // Fetch updated weather data
        fetch('/weather')
            .then(response => response.text())
            .then(html => {
                // Replace container with updated content
                weatherContainer.innerHTML = html;
                
                // Update icons
                updateWeatherIcons();
            })
            .catch(error => {
                console.error('Error refreshing weather data:', error);
                weatherContainer.innerHTML = '<p class="text-danger">Error loading weather data. Please try again.</p>';
            });
    }
}
