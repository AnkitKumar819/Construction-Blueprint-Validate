// File handling
let selectedFile = null;
let selectedImageURL = null;

const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const dropZone = document.getElementById('drop-zone');
const uploadPreview = document.getElementById('upload-preview');
const fileName = document.getElementById('file-name');
const removeFileBtn = document.getElementById('remove-file-btn');
const imagePreview = document.getElementById('image-preview');
const selectedImage = document.getElementById('selected-image');
const resultImage = document.getElementById('result-image');
const analyzeBtn = document.getElementById('analyze-btn');
const uploadPanel = document.getElementById('upload-panel');
const resultsPanel = document.getElementById('results-panel');
const verificationPanel = document.getElementById('verification-panel');
const verificationList = document.getElementById('verification-list');
const violationsPanel = document.getElementById('violations-panel');
const violationsList = document.getElementById('violations-list');
const solutionsPanel = document.getElementById('solutions-panel');
const solutionsList = document.getElementById('solutions-list');
const resetBtn = document.getElementById('reset-btn');

const loader = document.getElementById('loader');

// Chat elements
const chatToggleBtn = document.getElementById('chat-toggle-btn');
const closeChatBtn = document.getElementById('close-chat-btn');
const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatMessages = document.getElementById('chat-messages');

// Browse button click
browseBtn.addEventListener('click', () => {
    fileInput.click();
});

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        updateFilePreview();
    }
});

// Drag and drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#4f46e5';
    dropZone.style.backgroundColor = 'rgba(79, 70, 229, 0.05)';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = '#e5e7eb';
    dropZone.style.backgroundColor = 'transparent';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#e5e7eb';
    dropZone.style.backgroundColor = 'transparent';
    
    if (e.dataTransfer.files.length > 0) {
        selectedFile = e.dataTransfer.files[0];
        updateFilePreview();
    }
});

// Update file preview
function updateFilePreview() {
    if (!selectedFile) {
        return;
    }

    fileName.textContent = selectedFile.name;
    dropZone.classList.add('hidden');
    uploadPreview.classList.remove('hidden');
    analyzeBtn.disabled = false;

    if (selectedImageURL) {
        URL.revokeObjectURL(selectedImageURL);
        selectedImageURL = null;
    }

    if (selectedFile.type.startsWith('image/')) {
        selectedImageURL = URL.createObjectURL(selectedFile);
        selectedImage.src = selectedImageURL;
        imagePreview.classList.remove('hidden');
    } else {
        selectedImage.src = '';
        imagePreview.classList.add('hidden');
    }
}

// Remove file
removeFileBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    uploadPreview.classList.add('hidden');
    dropZone.classList.remove('hidden');
    analyzeBtn.disabled = true;
});

// Analyze button
analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    uploadPanel.classList.add('hidden');
    loader.classList.remove('hidden');
    resultsPanel.classList.add('hidden');
    
    await submitBlueprint();
});

// Submit blueprint to API
async function submitBlueprint() {
    try {
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        // Set a timeout for the request (30 seconds)
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 30000);
        
        const response = await fetch('http://localhost:8000/validate', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeout);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Check if there are errors in the response
        if (result.errors && result.errors.length > 0) {
            throw new Error(`Backend error: ${result.errors.join(', ')}`);
        }
        
        displayResults(result);
    } catch (error) {
        console.error('Error:', error);
        loader.classList.add('hidden');
        uploadPanel.classList.remove('hidden');
        
        // Show user-friendly error message
        let errorMsg = 'Error analyzing blueprint: ';
        if (error.name === 'AbortError') {
            errorMsg += 'Request timed out. Please check if the backend server is running on http://localhost:8000';
        } else {
            errorMsg += error.message;
        }
        
        // Display error in a styled alert panel instead of browser alert
        showErrorPanel(errorMsg);
    }
}

// Show error message in a styled panel
function showErrorPanel(message) {
    // Check if error panel already exists
    let errorPanel = document.getElementById('error-panel');
    if (!errorPanel) {
        errorPanel = document.createElement('div');
        errorPanel.id = 'error-panel';
        errorPanel.className = 'error-panel glass-panel';
        document.querySelector('.upload-section').insertAdjacentElement('afterend', errorPanel);
    }
    
    errorPanel.innerHTML = `
        <div class="error-content">
            <i data-lucide="alert-circle" class="error-icon"></i>
            <div>
                <h3>Analysis Failed</h3>
                <p>${escapeHtml(message)}</p>
            </div>
            <button class="btn-secondary" onclick="document.getElementById('error-panel').classList.add('hidden')">
                <i data-lucide="x"></i>
            </button>
        </div>
    `;
    
    errorPanel.classList.remove('hidden');
    lucide.createIcons(); // Recreate icons
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        if (errorPanel && !errorPanel.classList.contains('hidden')) {
            errorPanel.classList.add('hidden');
        }
    }, 10000);
}

// Display results
function displayResults(data) {
    loader.classList.add('hidden');
    resultsPanel.classList.remove('hidden');
    
    if (resultImage) {
        resultImage.src = selectedImageURL || '';
        resultImage.style.display = selectedImageURL ? 'block' : 'none';
    }

    // Determine compliance status
    const hasErrors = data.errors && data.errors.length > 0;
    const statusBadge = document.getElementById('status-badge');
    const statusClass = hasErrors ? 'status-failed' : 'status-passed';
    const statusText = hasErrors ? '❌ Non-Compliant' : '✓ Compliant';
    
    statusBadge.className = `status-badge ${statusClass}`;
    statusBadge.textContent = statusText;
    
    // Display errors
    const errorsContainer = document.getElementById('errors-container');
    const errorsList = document.getElementById('errors-list');
    if (hasErrors) {
        errorsContainer.classList.remove('hidden');
        errorsList.innerHTML = data.errors
            .map(err => `<li>${escapeHtml(err)}</li>`)
            .join('');
    } else {
        errorsContainer.classList.add('hidden');
    }
    
    // Display analysis
    const analysisText = document.getElementById('analysis-text');
    analysisText.textContent = (data.compliance_report?.reasoning || data.analysis || 'No analysis available');

    // Display verification details
    const specs = data.extracted_specs || {};
    verificationList.innerHTML = '';
    if (Object.keys(specs).length > 0) {
        verificationPanel.classList.remove('hidden');
        verificationList.innerHTML = [
            `Square footage: ${specs.sq_ft ?? 'unknown'}`,
            `Height: ${specs.height ?? 'unknown'} ft`,
            `Setbacks (ft): front=${specs.setbacks?.front ?? 'n/a'}, rear=${specs.setbacks?.rear ?? 'n/a'}, left=${specs.setbacks?.left ?? 'n/a'}, right=${specs.setbacks?.right ?? 'n/a'}`,
            `Fire safety features: ${specs.fire_safety_exists ? 'present' : 'absent'}`,
        ]
            .map(item => `<li>${escapeHtml(item)}</li>`)
            .join('');
    } else {
        verificationPanel.classList.add('hidden');
    }

    // Display violations
    violationsList.innerHTML = '';
    if (data.compliance_report?.status === 'FAIL') {
        violationsPanel.classList.remove('hidden');
        const violations = (data.compliance_report.citations || []).map(c => {
            const excerpt = c.law_excerpt || c.text || '(dialing citations)';
            return `${excerpt} [${c.source_link || 'source'}]`;
        });
        if (violations.length === 0) {
            violationsList.innerHTML = '<li>No explicit citation details provided; check compliance report reasoning.</li>';
        } else {
            violationsList.innerHTML = violations.map(v => `<li>${escapeHtml(v)}</li>`).join('');
        }
    } else {
        violationsPanel.classList.add('hidden');
    }

    // Display suggested solutions
    solutionsList.innerHTML = '';
    solutionsPanel.classList.remove('hidden');
    const status = data.compliance_report?.status;
    if (status === 'PASS') {
        solutionsList.innerHTML = '<li>Blueprint appears compliant. Maintain current design and document citations.</li>';
    } else if (status === 'FAIL') {
        solutionsList.innerHTML = [
            'Re-check setback and height requirements from cited laws and adjust plans.',
            'Add or improve fire safety systems, exits, or sprinkler plans if required.',
            'If areas are ambiguous, consult local zoning officer and revise schematics accordingly.',
        ].map(s => `<li>${escapeHtml(s)}</li>`).join('');
    } else if (status === 'CLARIFICATION_NEEDED' || status === 'WARNING') {
        solutionsList.innerHTML = [
            'Provide more precise measurements or scale information in the blueprint.',
            'Clarify uncertain specs such as setbacks or building height.',
            'Resubmit once area and fire-safety details are clear.',
        ].map(s => `<li>${escapeHtml(s)}</li>`).join('');
    } else {
        solutionsList.innerHTML = '<li>Unable to derive solutions; check the backend for additional details.</li>';
    }

    // Display relevant laws (remove hash fragments from SOURCE_LINK)
    const lawsList = document.getElementById('laws-list');
    if (data.relevant_laws && data.relevant_laws.length > 0) {
        lawsList.innerHTML = data.relevant_laws
            .map(law => {
                // Remove hash fragment from SOURCE_LINK
                const cleanedLaw = law.replace(/(SOURCE_LINK:\s*https?:\/\/[^\s]+)(#[^\s]*)/g, '$1');
                return `<li>${escapeHtml(cleanedLaw)}</li>`;
            })
            .join('');
    } else {
        lawsList.innerHTML = '<li>No laws retrieved.</li>';
    }
}

// Reset and start over
resetBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    uploadPreview.classList.add('hidden');
    dropZone.classList.remove('hidden');
    analyzeBtn.disabled = true;
    resultsPanel.classList.add('hidden');
    uploadPanel.classList.remove('hidden');
    imagePreview.classList.add('hidden');
    if (selectedImageURL) {
        URL.revokeObjectURL(selectedImageURL);
        selectedImageURL = null;
    }
    if (resultImage) {
        resultImage.src = '';
    }
    verificationPanel.classList.add('hidden');
    violationsPanel.classList.add('hidden');
    solutionsPanel.classList.add('hidden');
    verificationList.innerHTML = '';
    violationsList.innerHTML = '';
    solutionsList.innerHTML = '';
});

// Chat functionality
chatToggleBtn.addEventListener('click', () => {
    chatWindow.classList.toggle('hidden');
});

closeChatBtn.addEventListener('click', () => {
    chatWindow.classList.add('hidden');
});

// Send chat message
sendBtn.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
});

function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'message user-message';
    userMsgDiv.textContent = message;
    chatMessages.appendChild(userMsgDiv);
    
    chatInput.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Simulate AI response (can be connected to backend later)
    setTimeout(() => {
        const aiMsgDiv = document.createElement('div');
        aiMsgDiv.className = 'message ai-message';
        aiMsgDiv.textContent = 'I\'m processing your question about the compliance report...';
        chatMessages.appendChild(aiMsgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 500);
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize icons on page load
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
});
