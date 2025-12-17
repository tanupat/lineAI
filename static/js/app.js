// API Base URL
const API_BASE = '/api/v1';

// State
let conversationHistory = [];
let settings = {
    provider: 'ollama',
    useRag: true,
    systemPrompt: 'You are a helpful AI assistant. Be concise and friendly in your responses.',
    topK: 5
};

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const providerSelect = document.getElementById('provider-select');
const useRagCheckbox = document.getElementById('use-rag');
const clearChatBtn = document.getElementById('clear-chat');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initChat();
    initDocuments();
    initSettings();
    loadProviderStatus();
    loadHealth();
});

// Navigation
function initNavigation() {
    document.querySelectorAll('[data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;

            // Update active nav
            document.querySelectorAll('[data-page]').forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Show page
            document.querySelectorAll('.page-content').forEach(p => p.style.display = 'none');
            document.getElementById(`page-${page}`).style.display = 'block';

            // Load data if needed
            if (page === 'documents') loadDocuments();
            if (page === 'settings') loadHealth();
        });
    });
}

// Chat Functions
function initChat() {
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage('user', message);
        messageInput.value = '';
        messageInput.style.height = 'auto';

        // Show typing indicator
        showTypingIndicator();

        try {
            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    provider: providerSelect.value,
                    use_rag: useRagCheckbox.checked,
                    conversation_history: conversationHistory,
                    system_prompt: settings.systemPrompt
                })
            });

            hideTypingIndicator();

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get response');
            }

            const data = await response.json();
            addMessage('assistant', data.response, data.sources);

            // Update history
            conversationHistory.push({ role: 'user', content: message });
            conversationHistory.push({ role: 'assistant', content: data.response });

            // Keep last 20 messages
            if (conversationHistory.length > 20) {
                conversationHistory = conversationHistory.slice(-20);
            }

        } catch (error) {
            hideTypingIndicator();
            showToast('Error', error.message, 'danger');
            addMessage('assistant', `Error: ${error.message}`);
        }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });

    // Send on Enter (Shift+Enter for new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Clear chat
    clearChatBtn.addEventListener('click', () => {
        conversationHistory = [];
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <i class="bi bi-robot display-1 text-primary"></i>
                <h5>Welcome to LINE AI Chatbot</h5>
                <p class="text-muted">Start a conversation or upload documents for RAG</p>
            </div>
        `;
    });
}

function addMessage(role, content, sources = null) {
    // Remove welcome message if exists
    const welcome = chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = role === 'user' ? '<i class="bi bi-person"></i>' : '<i class="bi bi-robot"></i>';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Parse markdown for assistant messages
    if (role === 'assistant') {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }

    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';
        sourcesDiv.innerHTML = `<i class="bi bi-file-earmark-text"></i> Sources: ${sources.join(', ')}`;
        contentDiv.appendChild(sourcesDiv);
    }

    if (role === 'user') {
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(avatar);
    } else {
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'message assistant';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = `
        <div class="message-avatar"><i class="bi bi-robot"></i></div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

// Documents Functions
function initDocuments() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) uploadFile(files[0]);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadFile(fileInput.files[0]);
            fileInput.value = '';
        }
    });

    document.getElementById('refresh-docs').addEventListener('click', loadDocuments);
}

async function uploadFile(file) {
    const progress = document.getElementById('upload-progress');
    const progressBar = progress.querySelector('.progress-bar');
    const status = document.getElementById('upload-status');

    progress.style.display = 'block';
    progressBar.style.width = '0%';
    status.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        // Simulate progress
        let percent = 0;
        const interval = setInterval(() => {
            percent += 10;
            if (percent <= 90) progressBar.style.width = percent + '%';
        }, 200);

        const response = await fetch(`${API_BASE}/rag/upload`, {
            method: 'POST',
            body: formData
        });

        clearInterval(interval);
        progressBar.style.width = '100%';

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();
        status.textContent = data.message;
        showToast('Success', `Document uploaded: ${data.chunks_created} chunks created`, 'success');

        setTimeout(() => {
            progress.style.display = 'none';
        }, 2000);

        loadDocuments();

    } catch (error) {
        progressBar.classList.add('bg-danger');
        status.textContent = `Error: ${error.message}`;
        showToast('Error', error.message, 'danger');
    }
}

async function loadDocuments() {
    const container = document.getElementById('documents-list');

    try {
        const response = await fetch(`${API_BASE}/rag/documents`);
        const data = await response.json();

        document.getElementById('total-chunks').textContent = data.total_chunks || 0;

        if (!data.documents || data.documents.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-inbox display-4"></i>
                    <p>No documents uploaded</p>
                </div>
            `;
            return;
        }

        container.innerHTML = data.documents.map(doc => `
            <div class="document-item">
                <i class="bi bi-file-earmark-text"></i>
                <div class="document-info">
                    <div class="document-name">${doc}</div>
                </div>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteDocument('${doc}')">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `).join('');

    } catch (error) {
        container.innerHTML = `
            <div class="text-center text-danger py-4">
                <i class="bi bi-exclamation-triangle display-4"></i>
                <p>Failed to load documents</p>
            </div>
        `;
    }
}

async function deleteDocument(filename) {
    if (!confirm(`Delete "${filename}"?`)) return;

    try {
        const response = await fetch(`${API_BASE}/rag/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Delete failed');
        }

        showToast('Success', 'Document deleted', 'success');
        loadDocuments();

    } catch (error) {
        showToast('Error', error.message, 'danger');
    }
}

// Settings Functions
function initSettings() {
    const defaultProvider = document.getElementById('default-provider');
    const systemPrompt = document.getElementById('system-prompt');
    const topK = document.getElementById('top-k');
    const defaultRag = document.getElementById('default-rag');

    // Load from localStorage
    const saved = localStorage.getItem('chatbot-settings');
    if (saved) {
        settings = { ...settings, ...JSON.parse(saved) };
        defaultProvider.value = settings.provider;
        providerSelect.value = settings.provider;
        systemPrompt.value = settings.systemPrompt;
        topK.value = settings.topK;
        defaultRag.checked = settings.useRag;
        useRagCheckbox.checked = settings.useRag;
    }

    // Save on change
    const saveSettings = () => {
        settings.provider = defaultProvider.value;
        settings.systemPrompt = systemPrompt.value;
        settings.topK = parseInt(topK.value);
        settings.useRag = defaultRag.checked;

        providerSelect.value = settings.provider;
        useRagCheckbox.checked = settings.useRag;

        localStorage.setItem('chatbot-settings', JSON.stringify(settings));
        showToast('Success', 'Settings saved', 'success');
    };

    defaultProvider.addEventListener('change', saveSettings);
    systemPrompt.addEventListener('change', saveSettings);
    topK.addEventListener('change', saveSettings);
    defaultRag.addEventListener('change', saveSettings);
}

async function loadProviderStatus() {
    const container = document.getElementById('provider-status');

    try {
        const response = await fetch(`${API_BASE}/providers`);
        const data = await response.json();

        container.innerHTML = Object.entries(data).map(([name, info]) => `
            <span class="badge ${info.available ? 'bg-success' : 'bg-secondary'}">
                <i class="bi bi-${info.available ? 'check-circle' : 'x-circle'}"></i>
                ${name}
            </span>
        `).join('');

    } catch (error) {
        container.innerHTML = '<span class="badge bg-danger">Failed to load</span>';
    }
}

async function loadHealth() {
    const container = document.getElementById('health-status');

    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        const providers = data.providers || {};
        container.innerHTML = Object.entries(providers).map(([name, info]) => `
            <div class="health-item">
                <span>${name}</span>
                <span class="badge ${info.available ? 'bg-success' : 'bg-danger'}">
                    ${info.available ? 'Available' : 'Unavailable'}
                </span>
            </div>
        `).join('');

    } catch (error) {
        container.innerHTML = `
            <div class="text-danger">
                <i class="bi bi-exclamation-triangle"></i> Failed to connect to API
            </div>
        `;
    }
}

// Toast Notification
function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toast-title');
    const toastBody = document.getElementById('toast-body');

    toast.className = `toast bg-${type} text-white`;
    toastTitle.textContent = title;
    toastBody.textContent = message;

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}
