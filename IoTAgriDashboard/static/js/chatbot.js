// Chatbot functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize chat
    initializeChat();
    
    // Set up suggested questions
    setupSuggestedQuestions();
    
    // Set up refresh analyses
    setupRefreshAnalyses();
    
    // Set up clear chat
    setupClearChat();

    // Animation pour le démarrage
    animateInitialElements();
});

function animateInitialElements() {
    // Animer l'icône du robot dans l'en-tête
    const robotIcon = document.querySelector('.card-header .fas.fa-robot');
    if (robotIcon) {
        robotIcon.classList.add('pulse-alert');
    }

    // Animer les éléments principaux avec un délai
    const mainElements = document.querySelectorAll('.card');
    mainElements.forEach((element, index) => {
        setTimeout(() => {
            element.style.opacity = '0';
            element.classList.add('animate-message');
            element.style.opacity = '1';
        }, 100 * index);
    });
}

function initializeChat() {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    
    if (chatForm) {
        chatForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const message = userInput.value.trim();
            if (message) {
                // Add user message to the chat
                addUserMessage(message);
                
                // Clear input
                userInput.value = '';
                
                // Show typing indicator
                showTypingIndicator();
                
                // Send message to backend
                sendMessageToAI(message);
            }
        });
    }
}

function addUserMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    messageElement.className = 'chat-message user-message animate-message';
    
    messageElement.innerHTML = `
        <div class="chat-avatar">
            <i class="fas fa-user"></i>
        </div>
        <div class="chat-bubble">
            <p>${escapeHTML(message)}</p>
        </div>
    `;
    
    chatMessages.appendChild(messageElement);
    
    // Appliquer l'animation après ajout de l'élément
    setTimeout(() => {
        messageElement.style.opacity = '1';
    }, 10);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addAIMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    messageElement.className = 'chat-message ai-message animate-message';
    
    // Format the message with Markdown-like formatting
    const formattedMessage = formatMessage(message);
    
    messageElement.innerHTML = `
        <div class="chat-avatar assistant-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="chat-bubble">
            ${formattedMessage}
        </div>
    `;
    
    chatMessages.appendChild(messageElement);
    
    // Animer le message avec un effet de frappe séquentiel
    const chatBubble = messageElement.querySelector('.chat-bubble');
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Ajouter des classes d'animation pour les éléments spéciaux
    // Comme les conseils agricoles, alertes, etc.
    highlightSpecialContent(messageElement);
}

function highlightSpecialContent(messageElement) {
    // Mettre en évidence les conseils agricoles
    if (messageElement.textContent.toLowerCase().includes('conseil') || 
        messageElement.textContent.toLowerCase().includes('recommand')) {
        const paragraphs = messageElement.querySelectorAll('p');
        paragraphs.forEach(p => {
            if (p.textContent.toLowerCase().includes('conseil') || 
                p.textContent.toLowerCase().includes('recommand')) {
                p.classList.add('farming-tip', 'highlight-recommendation');
            }
        });
    }
    
    // Mettre en évidence les alertes
    if (messageElement.textContent.toLowerCase().includes('alert') || 
        messageElement.textContent.toLowerCase().includes('attention') ||
        messageElement.textContent.toLowerCase().includes('urgent')) {
        const paragraphs = messageElement.querySelectorAll('p');
        paragraphs.forEach(p => {
            if (p.textContent.toLowerCase().includes('alert') || 
                p.textContent.toLowerCase().includes('attention') ||
                p.textContent.toLowerCase().includes('urgent')) {
                p.classList.add('threshold-alert', 'pulse-alert');
            }
        });
    }
    
    // Mettre en évidence les données météorologiques
    if (messageElement.textContent.toLowerCase().includes('pluie') || 
        messageElement.textContent.toLowerCase().includes('soleil') ||
        messageElement.textContent.toLowerCase().includes('température')) {
        const paragraphs = messageElement.querySelectorAll('p');
        paragraphs.forEach(p => {
            if (p.textContent.toLowerCase().includes('pluie')) {
                p.classList.add('weather-icon', 'rain');
            } else if (p.textContent.toLowerCase().includes('soleil')) {
                p.classList.add('weather-icon', 'sun');
            }
        });
    }
}

function showTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.classList.remove('d-none');
    }
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.classList.add('d-none');
    }
}

function sendMessageToAI(message) {
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Hide typing indicator
        hideTypingIndicator();
        
        // Add AI response to the chat
        addAIMessage(data.response);
    })
    .catch(error => {
        console.error('Error sending message:', error);
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Add error message
        addAIMessage("Désolé, j'ai rencontré un problème lors du traitement de votre message. Veuillez réessayer plus tard.");
    });
}

function formatMessage(message) {
    // Replace newlines with <br>
    let formatted = message.replace(/\n/g, '<br>');
    
    // Bold text between ** **
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong class="data-value-change">$1</strong>');
    
    // Italic text between * *
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Lists (simple)
    formatted = formatted.replace(/- (.*?)(?:\n|$)/g, '<li>$1</li>');
    
    // Wrap lists in <ul>
    if (formatted.includes('<li>')) {
        formatted = formatted.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    }
    
    return formatted;
}

function escapeHTML(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function setupSuggestedQuestions() {
    const suggestedQuestions = document.querySelectorAll('.suggested-question');
    const userInput = document.getElementById('user-input');
    
    suggestedQuestions.forEach((button, index) => {
        // Ajouter un délai d'animation pour chaque question suggérée
        setTimeout(() => {
            button.classList.add('animate-message');
        }, 150 * index);
        
        button.addEventListener('click', function() {
            const question = this.textContent.trim();
            
            // Ajouter une animation lors du clic
            this.classList.add('pulse-alert');
            setTimeout(() => {
                this.classList.remove('pulse-alert');
            }, 500);
            
            // Set input value
            if (userInput) {
                userInput.value = question;
                userInput.focus();
            }
        });
    });
}

function setupRefreshAnalyses() {
    const refreshButton = document.getElementById('refresh-analyses');
    
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            // Ajouter une animation de rotation pendant le chargement
            const icon = this.querySelector('i');
            icon.classList.add('rotate-icon');
            
            refreshAnalyses().then(() => {
                // Enlever l'animation après le chargement
                setTimeout(() => {
                    icon.classList.remove('rotate-icon');
                }, 1000);
            });
        });
    }
}

function refreshAnalyses() {
    return fetch('/api/analyses')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateAnalysesTable(data.analyses);
        })
        .catch(error => {
            console.error('Error refreshing analyses:', error);
        });
}

function updateAnalysesTable(analyses) {
    const analysesTable = document.getElementById('analyses-table');
    
    if (analysesTable) {
        if (analyses && analyses.length > 0) {
            let html = '';
            
            analyses.forEach((analysis, index) => {
                html += `
                    <tr class="animate-message" style="animation-delay: ${index * 100}ms">
                        <td>${formatDate(analysis.timestamp)}</td>
                        <td class="text-truncate" style="max-width: 250px;">${analysis.analysis_text}</td>
                        <td class="text-truncate" style="max-width: 250px;">${analysis.recommendations}</td>
                    </tr>
                `;
            });
            
            analysesTable.innerHTML = html;
        } else {
            analysesTable.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center">Aucune analyse précédente disponible.</td>
                </tr>
            `;
        }
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function setupClearChat() {
    const clearButton = document.getElementById('clear-chat');
    const chatMessages = document.getElementById('chat-messages');
    
    if (clearButton && chatMessages) {
        clearButton.addEventListener('click', function() {
            // Animer le bouton
            this.classList.add('pulse-alert');
            setTimeout(() => {
                this.classList.remove('pulse-alert');
            }, 500);
            
            // Effet de disparition progressive sur tous les messages
            const messages = chatMessages.querySelectorAll('.chat-message');
            messages.forEach((msg, index) => {
                setTimeout(() => {
                    msg.style.opacity = '0';
                    msg.style.transform = 'translateY(20px)';
                }, 50 * index);
            });
            
            // Supprimer les messages après l'animation
            setTimeout(() => {
                // Keep only the first welcome message
                const welcomeMessage = chatMessages.querySelector('.chat-message');
                chatMessages.innerHTML = '';
                if (welcomeMessage) {
                    welcomeMessage.style.opacity = '0';
                    chatMessages.appendChild(welcomeMessage);
                    setTimeout(() => {
                        welcomeMessage.style.opacity = '1';
                        welcomeMessage.style.transform = 'translateY(0)';
                    }, 100);
                }
            }, messages.length * 50 + 300);
        });
    }
}
