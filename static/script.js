// Global variables for voice recognition
let isListening = false;
let recognition = null;

// Chat functionality
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    const chatHistory = document.getElementById('chatHistory');
    const loadingIndicator = document.getElementById('loadingIndicator');

    // Auto-focus message input
    if (messageInput) {
        messageInput.focus();
    }

    // Scroll to bottom of chat history
    if (chatHistory) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // Handle character limit
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            const maxLength = this.getAttribute('maxlength');
            const currentLength = this.value.length;

            if (currentLength >= maxLength) {
                this.value = this.value.slice(0, maxLength);
                this.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
                setTimeout(() => {
                    this.style.backgroundColor = 'transparent';
                }, 200);
            }
        });
    }

    // Initialize voice recognition
    setupVoiceRecognition();
});

// Send message function
function sendMessage(event) {
    if (event) event.preventDefault();
    const messageInput = document.getElementById('messageInput');
    const languageSelect = document.getElementById('languageSelect');
    const message = messageInput.value.trim();
    const language = languageSelect ? languageSelect.value : 'en';

    if (!message) return false;

    // Show loading indicator
    const loadingIndicator = document.getElementById('loadingIndicator');
    const sendBtn = document.getElementById('sendBtn');

    if (loadingIndicator) loadingIndicator.style.display = 'flex';
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    // Add user message immediately
    appendMessage(message, 'user');

    // Clear input
    messageInput.value = '';

    // Send message to server
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ message: message, language: language })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success' && data.messages && data.messages.length > 0) {
            // Only append the bot's response (user's message already appended)
            data.messages.forEach(msg => {
                if (msg.role === 'bot' && msg.content) {
                    appendMessage(msg.content, 'bot');
                }
            });
        } else {
            throw new Error(data.message || 'Failed to get response');
        }
    })
    .catch(error => {
        appendMessage('Sorry, there was an error processing your message. Please try again.', 'bot');
    })
    .finally(() => {
        // Hide loading indicator and reset button
        if (loadingIndicator) loadingIndicator.style.display = 'none';
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
        messageInput.focus();
    });

    return false;
}

// Append message to chat
function appendMessage(content, role) {
    const chatHistory = document.getElementById('chatHistory');
    if (!chatHistory) return;

    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${role}`;

    // Create avatar
    const avatar = document.createElement('div');
    avatar.className = `avatar ${role}`;
    const icon = document.createElement('i');
    icon.className = role === 'bot' ? 'fas fa-robot' : 'fas fa-user';
    avatar.appendChild(icon);

    // Create message container
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    // Create message content div
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = content;
    messageDiv.appendChild(contentDiv);

    // Create timestamp
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: 'numeric',
        hour12: true
    });
    messageDiv.appendChild(timeDiv);

    // Assemble message
    wrapper.appendChild(avatar);
    wrapper.appendChild(messageDiv);
    chatHistory.appendChild(wrapper);

    // Scroll to bottom
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Voice recognition setup
function setupVoiceRecognition() {
    const voiceBtn = document.getElementById('voiceBtn');
    const messageInput = document.getElementById('messageInput');

    // Check if speech recognition is supported
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        if (voiceBtn) {
            voiceBtn.style.display = 'none';
            console.log('Speech recognition not supported in this browser');
        }
        return;
    }

    // Initialize speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    let recognitionActive = false;
    let recognitionTimeout = null;

    recognition.onstart = () => {
        isListening = true;
        recognitionActive = true;
        if (voiceBtn) {
            voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
            voiceBtn.classList.add('listening');
            voiceBtn.style.color = '#ff6b6b';
        }
        showStatus('Listening... Speak now!');
        // Kill after 10 seconds if no result to avoid network error
        recognitionTimeout = setTimeout(() => {
            if (recognitionActive) {
                recognition.stop();
                showError('Microphone timed out. Please try again.');
            }
        }, 10000);
    };

    recognition.onresult = (event) => {
        recognitionActive = false;
        clearTimeout(recognitionTimeout);
        const transcript = event.results[0][0].transcript;
        if (messageInput) {
            messageInput.value = transcript;
        }
        showStatus('Captured: ' + transcript);

        // Auto-send after a short delay
        setTimeout(() => {
            if (messageInput && messageInput.value.trim()) {
                sendMessage(new Event('submit'));
            }
        }, 1000);
    };

    recognition.onerror = (event) => {
        recognitionActive = false;
        clearTimeout(recognitionTimeout);
        console.error('Speech recognition error:', event.error);
        let errorMessage = 'Failed to recognize speech. Please try again.';

        switch(event.error) {
            case 'no-speech':
                errorMessage = 'No speech detected. Please try again.';
                break;
            case 'audio-capture':
                errorMessage = 'Microphone access denied. Please allow microphone access.';
                break;
            case 'not-allowed':
                errorMessage = 'Microphone access denied. Please allow microphone access.';
                break;
            case 'network':
                errorMessage = 'Network error. Please check your connection.';
                break;
            case 'aborted':
                errorMessage = 'Microphone stopped. Please try again.';
                break;
        }

        showError(errorMessage);
        resetVoiceButton();
    };

    recognition.onend = () => {
        recognitionActive = false;
        clearTimeout(recognitionTimeout);
        resetVoiceButton();
    };

    // Add click event listener to voice button
    if (voiceBtn) {
        voiceBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            if (!isListening) {
                try {
                    recognition.start();
                } catch (error) {
                    console.error('Error starting speech recognition:', error);
                    showError('Failed to start voice recognition. Please try again.');
                }
            } else {
                recognition.stop();
            }
        });
    }

    function resetVoiceButton() {
        isListening = false;
        if (voiceBtn) {
            voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            voiceBtn.classList.remove('listening');
            voiceBtn.style.color = '';
        }
    }
}

// --- Delete chat confirmation with better error handling and feedback ---
function confirmDelete(chatId, chatName) {
    if (confirm(`Are you sure you want to delete "${chatName}"?`)) {
        // Find the chat item
        const chatItem = document.querySelector(`.chat-item[data-id="${chatId}"]`);
        const deleteBtn = chatItem ? chatItem.querySelector('.delete-btn') : null;

        // Show loading state
        if (deleteBtn) {
            deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            deleteBtn.disabled = true;
        }
        if (chatItem) {
            chatItem.classList.add('deleting');
        }

        // Perform deletion with fetch and proper error handling
        fetch(`/delete_chat/${chatId}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.message || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Animate removal of chat item
                if (chatItem) {
                    chatItem.style.height = chatItem.offsetHeight + 'px';
                    chatItem.offsetHeight; // Force reflow
                    chatItem.style.height = '0';
                    chatItem.style.opacity = '0';
                    chatItem.style.marginTop = '0';
                    chatItem.style.marginBottom = '0';

                    setTimeout(() => {
                        chatItem.remove();
                        // If no chats left or redirect URL provided, handle accordingly
                        if (data.redirect) {
                            window.location.href = data.redirect;
                        } else if (document.querySelectorAll('.chat-item').length === 0) {
                            window.location.reload();
                        }
                    }, 300);
                } else {
                    // If chat item not found, just redirect
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    } else {
                        window.location.reload();
                    }
                }
            } else {
                throw new Error(data.message || 'Failed to delete chat');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // Reset the delete button
            if (deleteBtn) {
                deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                deleteBtn.disabled = false;
            }
            if (chatItem) {
                chatItem.classList.remove('deleting');
            }
            alert(error.message || 'Failed to delete chat. Please try again.');
        });
    }
}

// Ensure New Chat and Logout buttons do a full page reload
document.querySelectorAll('.btn.btn-primary, .btn.btn-danger').forEach(btn => {
    btn.addEventListener('click', function(e) {
        // Let default navigation happen (full reload)
    });
});

// Handle chat item animations
document.addEventListener('DOMContentLoaded', function() {
    // Add data-id attributes to chat items if not already present
    document.querySelectorAll('.chat-item').forEach(item => {
        if (!item.hasAttribute('data-id')) {
            const chatId = item.querySelector('.chat-link').href.split('/').pop();
            item.setAttribute('data-id', chatId);
        }
    });

    // Add transition class to chat items
    document.querySelectorAll('.chat-item').forEach(item => {
        item.style.transition = 'all 0.3s ease';
    });
});

// Utility functions
function scrollToBottom() {
    const chatBox = document.getElementById('chatBox');
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

function showLoading(show) {
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.innerHTML = show ?
            '<i class="fas fa-spinner fa-spin"></i>' :
            '<i class="fas fa-paper-plane"></i>';
        sendBtn.disabled = show;
    }
}

function showStatus(message) {
    let container = document.getElementById('status-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'status-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            max-width: 400px;
            text-align: center;
        `;
        document.body.appendChild(container);
    }

    const status = document.createElement('div');
    status.className = 'status-message';
    status.style.cssText = `
        background: #28a745;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        margin-bottom: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease;
    `;
    status.textContent = message;

    container.appendChild(status);

    setTimeout(() => {
        status.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (status.parentNode) {
                status.remove();
            }
        }, 300);
    }, 3000);
}

function showError(message) {
    let container = document.getElementById('status-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'status-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            max-width: 400px;
            text-align: center;
        `;
        document.body.appendChild(container);
    }

    const error = document.createElement('div');
    error.className = 'status-message error';
    error.style.cssText = `
        background: #dc3545;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        margin-bottom: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease;
    `;
    error.textContent = message;

    container.appendChild(error);

    setTimeout(() => {
        error.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (error.parentNode) {
                error.remove();
            }
        }, 300);
    }, 5000);
}