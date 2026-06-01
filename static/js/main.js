/**
 * AI File Sorter - Frontend Logic
 * Multi-provider AI support with settings management
 */

// State
let files = [];
let folders = [];
let existingFolders = [];
let currentDirectory = '';
let sortDirection = 'asc';
let chatHistory = [];
let currentSettings = {};
let availableProviders = {};

// DOM Elements - Main
const directoryInput = document.getElementById('directory');
const btnBrowse = document.getElementById('btn-browse');
const btnScan = document.getElementById('btn-scan');
const btnSuggest = document.getElementById('btn-suggest');
const btnPreview = document.getElementById('btn-preview');
const btnOrganize = document.getElementById('btn-organize');
const btnUndo = document.getElementById('btn-undo');
const fileList = document.getElementById('file-list');
const fileCount = document.getElementById('file-count');
const selectedCount = document.getElementById('selected-count');
const folderCount = document.getElementById('folder-count');
const selectAll = document.getElementById('select-all');
const statusBar = document.getElementById('status-bar');
const resultsModal = document.getElementById('results-modal');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');
const modalClose = document.getElementById('modal-close');
const modalOk = document.getElementById('modal-ok');

// DOM Elements - Options (inline chips)
const optUseFolders = document.getElementById('opt-use-folders');
const optRename = document.getElementById('opt-rename');
const optRecursive = document.getElementById('opt-recursive');
const optIncludeFolders = document.getElementById('opt-include-folders');
const optFoldersOnly = document.getElementById('opt-folders-only');
const customInstruction = document.getElementById('custom-instruction');

// DOM Elements - Filter/Search
const searchInput = document.getElementById('search-input');
const filterType = document.getElementById('filter-type');
const sortBy = document.getElementById('sort-by');
const btnSortDir = document.getElementById('btn-sort-dir');

// DOM Elements - AI Chat
const aiChat = document.getElementById('ai-chat');
const chatInput = document.getElementById('chat-input');
const btnSendChat = document.getElementById('btn-send-chat');
const btnClearChat = document.getElementById('btn-clear-chat');
const currentModelBadge = document.getElementById('current-model');
const folderSuggestions = document.getElementById('folder-suggestions');

// DOM Elements - Preview
const previewTree = document.getElementById('preview-tree');

// DOM Elements - Settings
const btnSettings = document.getElementById('btn-settings');
const settingsModal = document.getElementById('settings-modal');
const settingsClose = document.getElementById('settings-close');
const settingsCancel = document.getElementById('settings-cancel');
const settingsSave = document.getElementById('settings-save');
const providerSelect = document.getElementById('provider-select');
const modelSelect = document.getElementById('model-select');
const apiKeyInput = document.getElementById('api-key-input');
const btnToggleKey = document.getElementById('btn-toggle-key');
const currentKeyStatus = document.getElementById('current-key-status');
const customUrlGroup = document.getElementById('custom-url-group');
const customUrlInput = document.getElementById('custom-url-input');
const btnTestConnection = document.getElementById('btn-test-connection');
const connectionStatus = document.getElementById('connection-status');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Load settings and providers
    await loadSettings();
    await loadProviders();

    // Get default directory
    try {
        const response = await fetch('/api/default-directory');
        const data = await response.json();
        directoryInput.value = data.directory;
        currentDirectory = data.directory;
    } catch (e) {
        console.error('Failed to get default directory:', e);
    }

    // Event listeners - Main
    btnBrowse.addEventListener('click', browseFolder);
    btnScan.addEventListener('click', scanFiles);
    btnSuggest.addEventListener('click', getSuggestions);
    btnPreview.addEventListener('click', showPreview);
    btnOrganize.addEventListener('click', organizeFiles);
    btnUndo.addEventListener('click', undoOrganization);
    selectAll.addEventListener('change', toggleSelectAll);
    modalClose.addEventListener('click', closeModal);
    modalOk.addEventListener('click', closeModal);

    // Event listeners - Filter/Search
    searchInput.addEventListener('input', renderFiles);
    filterType.addEventListener('change', renderFiles);
    sortBy.addEventListener('change', renderFiles);
    btnSortDir.addEventListener('click', toggleSortDirection);

    // Event listeners - Chat
    btnSendChat.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
    btnClearChat.addEventListener('click', clearChat);

    // Event listeners - Settings
    btnSettings.addEventListener('click', openSettings);
    settingsClose.addEventListener('click', closeSettings);
    settingsCancel.addEventListener('click', closeSettings);
    settingsSave.addEventListener('click', saveSettings);
    providerSelect.addEventListener('change', onProviderChange);
    btnToggleKey.addEventListener('click', toggleApiKeyVisibility);
    btnTestConnection.addEventListener('click', testConnection);
    apiKeyInput.addEventListener('input', onApiKeyInput);

    // Close modals on outside click
    resultsModal.addEventListener('click', (e) => {
        if (e.target === resultsModal) closeModal();
    });
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettings();
    });

    // Option interactions
    optFoldersOnly.addEventListener('change', () => {
        if (optFoldersOnly.checked) {
            optIncludeFolders.checked = true;
            optIncludeFolders.disabled = true;
        } else {
            optIncludeFolders.disabled = false;
        }
    });
});

// Settings Functions
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();
        if (data.success) {
            currentSettings = data.settings;
            updateModelBadge();
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function loadProviders() {
    try {
        const response = await fetch('/api/providers');
        const data = await response.json();
        if (data.success) {
            availableProviders = data.providers;
        }
    } catch (e) {
        console.error('Failed to load providers:', e);
    }
}

function updateModelBadge() {
    if (currentSettings.provider_name && currentSettings.model) {
        // Get short model name
        const modelParts = currentSettings.model.split('/');
        const shortModel = modelParts[modelParts.length - 1];
        currentModelBadge.textContent = shortModel;
    } else {
        currentModelBadge.textContent = 'No API Key';
    }
}

function openSettings() {
    // Populate provider select
    providerSelect.innerHTML = '';
    Object.entries(availableProviders).forEach(([id, provider]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = provider.name;
        if (id === currentSettings.provider) {
            option.selected = true;
        }
        providerSelect.appendChild(option);
    });

    // Check if we have an API key set
    const hasApiKey = currentSettings.api_key_masked && currentSettings.api_key_masked !== 'Not set';

    if (hasApiKey) {
        // Load models for current provider
        loadModels(currentSettings.provider);
    } else {
        // Show prompt to enter API key first
        modelSelect.innerHTML = '<option value="">Enter API key first...</option>';
    }

    // Update UI
    currentKeyStatus.textContent = currentSettings.api_key_masked || 'Not set';
    customUrlInput.value = currentSettings.custom_base_url || '';

    // Show/hide custom URL field
    customUrlGroup.classList.toggle('hidden', providerSelect.value !== 'custom');

    // Clear connection status
    connectionStatus.textContent = '';
    apiKeyInput.value = '';

    settingsModal.classList.remove('hidden');
}

function closeSettings() {
    settingsModal.classList.add('hidden');
}

async function loadModels(providerId, apiKey = null) {
    try {
        // Show loading state
        modelSelect.innerHTML = '<option value="">Loading models...</option>';

        // Build URL with optional API key
        let url = `/api/models/${providerId}`;
        if (apiKey) {
            url += `?api_key=${encodeURIComponent(apiKey)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        modelSelect.innerHTML = '';

        if (data.success && data.models.length > 0) {
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.name}${model.vision ? ' 👁️' : ''}`;
                if (model.id === currentSettings.model) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = data.models?.length === 0 ? 'No models found' : 'Enter API key first...';
            modelSelect.appendChild(option);
        }
    } catch (e) {
        console.error('Failed to load models:', e);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
    }
}

function onProviderChange() {
    const providerId = providerSelect.value;
    const apiKey = apiKeyInput.value.trim();

    // Check if API key is entered
    if (apiKey) {
        loadModels(providerId, apiKey);
    } else if (currentSettings.api_key_masked && currentSettings.api_key_masked !== 'Not set') {
        loadModels(providerId);
    } else {
        modelSelect.innerHTML = '<option value="">Enter API key first...</option>';
    }

    customUrlGroup.classList.toggle('hidden', providerId !== 'custom');
    connectionStatus.textContent = '';
}

// Load models when API key is entered
function onApiKeyInput() {
    const apiKey = apiKeyInput.value.trim();
    if (apiKey.length > 10) {
        // API key looks valid, load models dynamically from provider API
        loadModels(providerSelect.value, apiKey);
    }
}

function toggleApiKeyVisibility() {
    const isPassword = apiKeyInput.type === 'password';
    apiKeyInput.type = isPassword ? 'text' : 'password';
    btnToggleKey.textContent = isPassword ? '🔒' : '👁️';
}

async function testConnection() {
    connectionStatus.textContent = 'Testing...';
    connectionStatus.className = '';

    try {
        // First save current settings
        const saveData = {
            provider: providerSelect.value,
            model: modelSelect.value
        };

        if (apiKeyInput.value) {
            saveData.api_key = apiKeyInput.value;
        }

        if (providerSelect.value === 'custom') {
            saveData.custom_base_url = customUrlInput.value;
        }

        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saveData)
        });

        // Now test
        const response = await fetch('/api/test-connection', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            connectionStatus.textContent = '✅ ' + data.message;
            connectionStatus.className = 'success';
        } else {
            connectionStatus.textContent = '❌ ' + data.message;
            connectionStatus.className = 'error';
        }
    } catch (e) {
        connectionStatus.textContent = '❌ ' + e.message;
        connectionStatus.className = 'error';
    }
}

async function saveSettings() {
    showStatus('Saving settings...', 'loading');

    try {
        const saveData = {
            provider: providerSelect.value,
            model: modelSelect.value
        };

        if (apiKeyInput.value) {
            saveData.api_key = apiKeyInput.value;
        }

        if (providerSelect.value === 'custom') {
            saveData.custom_base_url = customUrlInput.value;
        }

        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saveData)
        });

        const data = await response.json();

        if (data.success) {
            currentSettings = data.settings;
            updateModelBadge();
            closeSettings();
            showStatus('Settings saved!', 'success');
            addChatMessage('system', `🔧 Switched to **${currentSettings.provider_name}** - ${currentSettings.model}`);
            setTimeout(hideStatus, 2000);
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
    } catch (e) {
        showStatus(`Error: ${e.message}`, 'error');
    }
}

// Toggle sort direction
function toggleSortDirection() {
    sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    btnSortDir.textContent = sortDirection === 'asc' ? '↑' : '↓';
    renderFiles();
}

// Browse for folder using native Windows dialog via backend
async function browseFolder() {
    showStatus('Opening folder picker...', 'loading');
    btnBrowse.disabled = true;

    try {
        const response = await fetch('/api/browse-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            directoryInput.value = data.path;
            hideStatus();
            await scanFiles();
        } else {
            hideStatus();
        }
    } catch (e) {
        showStatus(`Error: ${e.message}`, 'error');
    } finally {
        btnBrowse.disabled = false;
    }
}

// Utility: Format file size
function formatSize(bytes) {
    if (!bytes) return '-';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Utility: Get file icon
function getFileIcon(extension, isFolder = false) {
    if (isFolder) return '📁';
    const icons = {
        '.pdf': '📄',
        '.doc': '📝', '.docx': '📝',
        '.xls': '📊', '.xlsx': '📊',
        '.ppt': '📽️', '.pptx': '📽️',
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.webp': '🖼️',
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵',
        '.mp4': '🎬', '.mkv': '🎬', '.avi': '🎬',
        '.zip': '📦', '.rar': '📦', '.7z': '📦',
        '.exe': '⚙️', '.msi': '⚙️',
        '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
        '.txt': '📃',
    };
    return icons[(extension || '').toLowerCase()] || '📄';
}

// Show status
function showStatus(message, type = 'loading') {
    statusBar.classList.remove('hidden', 'loading', 'success', 'error');
    statusBar.classList.add(type);
    statusBar.querySelector('.status-text').textContent = message;
    statusBar.querySelector('.status-icon').textContent =
        type === 'loading' ? '⏳' : type === 'success' ? '✅' : '❌';
}

function hideStatus() {
    statusBar.classList.add('hidden');
}

// Update counts
function updateCounts() {
    const allItems = files.concat(folders);
    const fileItems = files.length;
    const folderItems = folders.length;
    const selected = allItems.filter(f => f.action === 'move').length;

    fileCount.textContent = `${fileItems} files`;
    folderCount.textContent = `${folderItems} folders`;
    selectedCount.textContent = `${selected} selected`;
}

// Get filtered and sorted items
function getFilteredItems() {
    let allItems = [...files, ...folders];

    // Apply search filter
    const searchTerm = searchInput.value.toLowerCase().trim();
    if (searchTerm) {
        allItems = allItems.filter(f =>
            f.name.toLowerCase().includes(searchTerm) ||
            (f.category || '').toLowerCase().includes(searchTerm)
        );
    }

    // Apply type filter
    const typeFilter = filterType.value;
    if (typeFilter === 'files') {
        allItems = allItems.filter(f => !f.isFolder);
    } else if (typeFilter === 'folders') {
        allItems = allItems.filter(f => f.isFolder);
    }

    // Apply sorting
    const sortField = sortBy.value;
    allItems.sort((a, b) => {
        let comparison = 0;
        switch (sortField) {
            case 'name':
                comparison = a.name.localeCompare(b.name);
                break;
            case 'size':
                comparison = (a.size || 0) - (b.size || 0);
                break;
            case 'category':
                comparison = (a.category || '').localeCompare(b.category || '');
                break;
            case 'type':
                comparison = (a.isFolder ? 0 : 1) - (b.isFolder ? 0 : 1);
                break;
        }
        return sortDirection === 'asc' ? comparison : -comparison;
    });

    return allItems;
}

// Render file table
function renderFiles() {
    const items = getFilteredItems();

    if (items.length === 0) {
        fileList.innerHTML = `
            <tr class="empty-state">
                <td colspan="6">
                    <div class="empty-message">
                        <span class="empty-icon">📂</span>
                        <p>No items found</p>
                        <p class="empty-hint">Try a different search or filter</p>
                    </div>
                </td>
            </tr>
        `;
        btnSuggest.disabled = true;
        btnOrganize.disabled = true;
        btnPreview.disabled = true;
        return;
    }

    fileList.innerHTML = items.map((item, index) => `
        <tr data-name="${item.name}" data-folder="${item.isFolder || false}">
            <td class="col-checkbox">
                <input type="checkbox" class="item-checkbox" 
                    ${item.action === 'move' ? 'checked' : ''} 
                    onchange="toggleItem('${item.name}', ${item.isFolder || false})">
            </td>
            <td class="col-type">
                <span class="type-icon ${item.isFolder ? 'folder-icon' : ''}">${getFileIcon(item.extension, item.isFolder)}</span>
            </td>
            <td class="col-name">
                <div class="file-name">
                    <span>${item.name}</span>
                    ${item.new_name ? `<span class="rename-arrow">→</span><span class="new-name">${item.new_name}</span>` : ''}
                </div>
            </td>
            <td class="col-size">${formatSize(item.size)}</td>
            <td class="col-destination">
                <input type="text" class="destination-input" 
                    value="${item.category || ''}" 
                    placeholder="Destination..."
                    list="folder-suggestions"
                    onchange="updateDestination('${item.name.replace(/'/g, "\\'")}', ${item.isFolder || false}, this.value)">
            </td>
            <td class="col-action">
                <div class="action-toggle">
                    <button class="${item.action === 'move' ? 'active' : ''}" 
                        onclick="setAction('${item.name}', ${item.isFolder || false}, 'move')">Move</button>
                    <button class="${item.action === 'skip' ? 'active' : ''}" 
                        onclick="setAction('${item.name}', ${item.isFolder || false}, 'skip')">Skip</button>
                </div>
            </td>
        </tr>
    `).join('');

    btnSuggest.disabled = false;
    checkActionButtons();
    updateCounts();
}

// Toggle select all
function toggleSelectAll() {
    const checked = selectAll.checked;
    files.forEach(f => f.action = checked ? 'move' : 'skip');
    folders.forEach(f => f.action = checked ? 'move' : 'skip');
    renderFiles();
}

// Toggle individual item
function toggleItem(name, isFolder) {
    const list = isFolder ? folders : files;
    const item = list.find(f => f.name === name);
    if (item) {
        item.action = item.action === 'move' ? 'skip' : 'move';
        updateCounts();
        checkActionButtons();
    }
}

// Update destination
function updateDestination(name, isFolder, value) {
    const list = isFolder ? folders : files;
    const item = list.find(f => f.name === name);
    if (item) {
        item.category = value.trim();
        checkActionButtons();
    }
}

// Set action
function setAction(name, isFolder, action) {
    const list = isFolder ? folders : files;
    const item = list.find(f => f.name === name);
    if (item) {
        item.action = action;
        renderFiles();
    }
}

// Check if action buttons should be enabled
function checkActionButtons() {
    const allItems = files.concat(folders);
    const hasItemsToMove = allItems.some(f => f.action === 'move' && f.category);
    btnOrganize.disabled = !hasItemsToMove;
    btnPreview.disabled = !hasItemsToMove;
}

// API: Scan files
async function scanFiles() {
    const directory = directoryInput.value.trim();
    if (!directory) {
        alert('Please enter a directory path');
        return;
    }

    showStatus('Scanning directory...', 'loading');
    btnScan.disabled = true;

    try {
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                directory,
                recursive: optRecursive.checked,
                include_folders: optIncludeFolders.checked || optFoldersOnly.checked,
                folders_only: optFoldersOnly.checked
            })
        });

        const data = await response.json();

        if (data.success) {
            files = data.files || [];
            folders = data.folders_to_organize || [];
            existingFolders = data.existing_folders || [];
            currentDirectory = data.directory;
            currentDirectory = data.directory;
            updateFolderSuggestions();
            renderFiles();

            const msg = `Found ${files.length} files, ${folders.length} folders (${existingFolders.length} existing)`;
            showStatus(msg, 'success');

            // Add to chat
            addChatMessage('assistant', `📊 Scanned directory: **${currentDirectory}**\n\n- ${files.length} files found\n- ${folders.length} folders to organize\n- ${existingFolders.length} existing folders detected`);

            setTimeout(hideStatus, 3000);
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
    } catch (e) {
        showStatus(`Error: ${e.message}`, 'error');
    } finally {
        btnScan.disabled = false;
    }
}

// Helper: Update folder suggestions datalist
function updateFolderSuggestions() {
    // Collect all potential folder names
    const suggestions = new Set();

    // Add existing folders
    existingFolders.forEach(f => suggestions.add(f));

    // Add AI suggested categories
    files.forEach(f => {
        if (f.category && f.category !== 'Misc') suggestions.add(f.category);
    });
    folders.forEach(f => {
        if (f.category && f.category !== 'Misc' && f.category !== 'SKIP') suggestions.add(f.category);
    });

    // Common folders
    const common = ['Documents', 'Images', 'Videos', 'Music', 'Downloads', 'Archives', 'Code', 'Finance', 'Work', 'Personal'];
    common.forEach(c => suggestions.add(c));

    // Render options
    folderSuggestions.innerHTML = Array.from(suggestions).sort().map(f => `<option value="${f}">`).join('');
}

// API: Get AI suggestions
async function getSuggestions() {
    showStatus('Getting AI suggestions...', 'loading');
    btnSuggest.disabled = true;

    try {
        const response = await fetch('/api/suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                files: files.concat(folders),
                folders: optUseFolders.checked ? existingFolders : [],
                instruction: customInstruction.value.trim(),
                rename: optRename.checked
            })
        });

        const data = await response.json();

        if (data.success) {
            // Separate files and folders from response
            const responseItems = data.files || [];
            files = responseItems.filter(f => !f.isFolder);
            folders = responseItems.filter(f => f.isFolder);

            renderFiles();
            showStatus('AI suggestions applied!', 'success');

            // Show AI reasoning in chat
            if (data.reasoning) {
                addChatMessage('assistant', `🤖 **AI Analysis:**\n\n${data.reasoning}`);
            } else {
                addChatMessage('assistant', `✅ Applied suggestions to ${responseItems.length} items.\n\nReview the "Destination" column and click "Preview" to see the organization plan.`);
            }

            updateFolderSuggestions();
            setTimeout(hideStatus, 2000);
        } else {
            showStatus(`Error: ${data.error}`, 'error');
            addChatMessage('assistant', `❌ Error getting suggestions: ${data.error}`);
        }
    } catch (e) {
        showStatus(`Error: ${e.message}`, 'error');
    } finally {
        btnSuggest.disabled = false;
    }
}

// Show preview
function showPreview() {
    const allItems = files.concat(folders);
    const toMove = allItems.filter(f => f.action === 'move' && f.category);

    if (toMove.length === 0) {
        previewTree.innerHTML = '<p class="preview-hint">No items selected for organization</p>';
        return;
    }

    // Group by destination
    const byDestination = {};
    toMove.forEach(item => {
        const dest = item.category;
        if (!byDestination[dest]) {
            byDestination[dest] = [];
        }
        byDestination[dest].push(item);
    });

    // Render preview tree
    let html = '';
    Object.keys(byDestination).sort().forEach(dest => {
        const items = byDestination[dest];
        html += `
            <div class="preview-folder">
                <div class="preview-folder-name">
                    <span>📁</span> ${dest}
                    <span class="preview-file-count">(${items.length})</span>
                </div>
                <div class="preview-files">
                    ${items.slice(0, 5).map(f => `
                        <div class="preview-file">
                            <span>${getFileIcon(f.extension, f.isFolder)}</span>
                            ${f.new_name ? `${f.name} → ${f.new_name}` : f.name}
                        </div>
                    `).join('')}
                    ${items.length > 5 ? `<div class="preview-file">... and ${items.length - 5} more</div>` : ''}
                </div>
            </div>
        `;
    });

    previewTree.innerHTML = html;

    // Add summary to chat
    const summary = Object.keys(byDestination).map(d => `• **${d}**: ${byDestination[d].length} items`).join('\n');
    addChatMessage('assistant', `📋 **Organization Preview:**\n\n${summary}\n\nClick "Organize" to proceed.`);
}

// API: Organize files
async function organizeFiles() {
    const allItems = files.concat(folders);
    const toMove = allItems.filter(f => f.action === 'move' && f.category);

    if (toMove.length === 0) {
        alert('No items selected for organization');
        return;
    }

    if (!confirm(`Move ${toMove.length} items to their destinations?`)) {
        return;
    }

    showStatus('Organizing files...', 'loading');
    btnOrganize.disabled = true;

    try {
        const response = await fetch('/api/organize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: toMove })
        });

        const data = await response.json();

        if (data.success) {
            showResults('Organization Complete', data.results);
            addChatMessage('assistant', `✨ **Organization Complete!**\n\n- ✅ ${data.results.success?.length || 0} items moved successfully\n- ⏭️ ${data.results.skipped?.length || 0} items skipped\n- ❌ ${data.results.errors?.length || 0} errors`);
            await scanFiles();
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
    } catch (e) {
        showStatus(`Error: ${e.message}`, 'error');
    } finally {
        btnOrganize.disabled = false;
    }
}

// API: Undo organization
async function undoOrganization() {
    if (!confirm('Undo the last organization? Items will be moved back.')) {
        return;
    }

    showStatus('Undoing organization...', 'loading');
    btnUndo.disabled = true;

    try {
        const response = await fetch('/api/undo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            const results = data.results;
            if (results.error) {
                showStatus(results.error, 'error');
                addChatMessage('assistant', `⚠️ ${results.error}`);
            } else {
                showResults('Undo Complete', {
                    success: results.restored.map(name => ({ name })),
                    errors: results.errors.map(e => ({ name: e, error: '' })),
                    skipped: []
                });
                addChatMessage('assistant', `↩️ **Undo Complete!**\n\n- ${results.restored.length} items restored\n- ${results.folders_removed?.length || 0} empty folders removed`);
                await scanFiles();
            }
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
    } catch (e) {
        showStatus(`Error: ${e.message}`, 'error');
    } finally {
        btnUndo.disabled = false;
    }
}

// Chat functions
function addChatMessage(role, content) {
    chatHistory.push({ role, content });

    const messageDiv = document.createElement('div');
    messageDiv.className = `ai-message ${role}`;

    // Simple markdown-like formatting
    let html = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/• /g, '&bull; ');

    messageDiv.innerHTML = `<p>${html}</p>`;
    aiChat.appendChild(messageDiv);
    aiChat.scrollTop = aiChat.scrollHeight;
}

async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addChatMessage('user', message);
    chatInput.value = '';

    showStatus('AI is thinking...', 'loading');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                files: files.concat(folders),
                existing_folders: existingFolders,
                directory: currentDirectory
            })
        });

        const data = await response.json();

        if (data.success) {
            addChatMessage('assistant', data.response);
        } else {
            addChatMessage('assistant', `❌ Error: ${data.error}`);
        }
        hideStatus();
    } catch (e) {
        addChatMessage('assistant', `❌ Error: ${e.message}`);
        hideStatus();
    }
}

function clearChat() {
    chatHistory = [];
    aiChat.innerHTML = `
        <div class="ai-message system">
            <p>Chat cleared. How can I help with your files?</p>
        </div>
    `;
}

// Show results modal
function showResults(title, results) {
    modalTitle.textContent = title;

    let html = '';

    if (results.success && results.success.length > 0) {
        html += `
            <div class="result-section success">
                <h3>✅ Successfully Moved (${results.success.length})</h3>
                <ul class="result-list">
                    ${results.success.slice(0, 10).map(f => `<li>${f.name}${f.renamed_to ? ` → ${f.renamed_to}` : ''} → ${f.category || 'restored'}</li>`).join('')}
                    ${results.success.length > 10 ? `<li>... and ${results.success.length - 10} more</li>` : ''}
                </ul>
            </div>
        `;
    }

    if (results.skipped && results.skipped.length > 0) {
        html += `
            <div class="result-section skipped">
                <h3>⏭️ Skipped (${results.skipped.length})</h3>
                <ul class="result-list">
                    ${results.skipped.slice(0, 5).map(name => `<li>${name}</li>`).join('')}
                    ${results.skipped.length > 5 ? `<li>... and ${results.skipped.length - 5} more</li>` : ''}
                </ul>
            </div>
        `;
    }

    if (results.errors && results.errors.length > 0) {
        html += `
            <div class="result-section error">
                <h3>❌ Errors (${results.errors.length})</h3>
                <ul class="result-list">
                    ${results.errors.map(f => `<li>${f.name}: ${f.error}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    modalBody.innerHTML = html || '<p>No results to display.</p>';
    resultsModal.classList.remove('hidden');
    hideStatus();
}

// Close modal
function closeModal() {
    resultsModal.classList.add('hidden');
}
