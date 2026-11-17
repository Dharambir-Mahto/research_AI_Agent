/**
 * ResearchMatrix AI Agent - Frontend Application Logic
 * Ultra-Responsive, Zero-Bloat, Native Vanilla ES6
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let lastReport = null;
    let isResearching = false;
    let progressTimer = null;
    let currentSeconds = 0;
    let reportsData = [];
    let activeFilter = 'all';
    let currentConversationId = null;
    let conversationsData = [];

    // DOM Elements
    const chatContainer = document.getElementById('chat-container');
    const welcomeHero = document.getElementById('welcome-hero');
    const chatForm = document.getElementById('chat-form');
    const promptInput = document.getElementById('prompt-input');
    const sendBtn = document.getElementById('send-btn');
    const reportsDrawer = document.getElementById('reports-drawer');
    const drawerBackdrop = document.getElementById('drawer-backdrop');
    const toggleDrawerBtn = document.getElementById('toggle-drawer-btn');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const reportsList = document.getElementById('reports-list');
    const reportsCountBadge = document.getElementById('reports-count-badge');
    const drawerCountBadge = document.getElementById('drawer-count-badge');
    const reportSearch = document.getElementById('report-search');
    const filterTabs = document.querySelectorAll('.filter-tab');
    const previewModal = document.getElementById('preview-modal');
    const closePreviewBtn = document.getElementById('close-preview-btn');
    const previewTitle = document.getElementById('preview-title');
    const previewContent = document.getElementById('preview-content');
    const previewDownloadBtn = document.getElementById('preview-download-btn');
    const resetSessionBtn = document.getElementById('reset-session-btn');
    const agentStatusPill = document.getElementById('agent-status-pill');

    // Conversation History Elements
    const historyDrawer = document.getElementById('history-drawer');
    const toggleHistoryBtn = document.getElementById('toggle-history-btn');
    const closeHistoryBtn = document.getElementById('close-history-btn');
    const historyList = document.getElementById('history-list');
    const historyCountBadge = document.getElementById('history-count-badge');
    const historySearch = document.getElementById('history-search');
    const historyNewChatBtn = document.getElementById('history-new-chat-btn');
    const clearAllHistoryBtn = document.getElementById('clear-all-history-btn');

    // Theme Switcher Elements
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeIconSun = document.getElementById('theme-icon-sun');
    const themeIconMoon = document.getElementById('theme-icon-moon');

    function initTheme() {
        const isLight = document.documentElement.classList.contains('light');
        if (themeIconSun && themeIconMoon) {
            if (isLight) {
                themeIconSun.classList.add('hidden');
                themeIconMoon.classList.remove('hidden');
            } else {
                themeIconSun.classList.remove('hidden');
                themeIconMoon.classList.add('hidden');
            }
        }
        if (window.lucide) lucide.createIcons();
    }

    function toggleTheme() {
        const isLight = document.documentElement.classList.contains('light');
        if (isLight) {
            document.documentElement.classList.remove('light');
            document.documentElement.classList.add('dark');
            localStorage.setItem('omni_theme', 'dark');
            if (themeIconSun) themeIconSun.classList.remove('hidden');
            if (themeIconMoon) themeIconMoon.classList.add('hidden');
            showToast('Switched to Dark Mode', 'info');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.classList.add('light');
            localStorage.setItem('omni_theme', 'light');
            if (themeIconSun) themeIconSun.classList.add('hidden');
            if (themeIconMoon) themeIconMoon.classList.remove('hidden');
            showToast('Switched to Light Mode', 'info');
        }
        if (window.lucide) lucide.createIcons();
        renderReportsList();
        renderHistoryList();
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
    initTheme();

    // Configure Marked.js for safe, beautiful markdown rendering
    if (window.marked) {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            highlight: function(code, lang) {
                if (window.hljs) {
                    if (lang && hljs.getLanguage(lang)) {
                        try { return hljs.highlight(code, { language: lang }).value; } catch (e) {}
                    }
                    try { return hljs.highlightAuto(code).value; } catch (e) {}
                }
                return code;
            }
        });
    }

    // Auto-grow textarea
    promptInput.addEventListener('input', () => {
        promptInput.style.height = 'auto';
        promptInput.style.height = Math.min(promptInput.scrollHeight, 160) + 'px';
    });

    // Enter to send (Shift+Enter for new line)
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Quick suggestion cards
    document.querySelectorAll('.suggestion-card').forEach(card => {
        card.addEventListener('click', () => {
            const prompt = card.getAttribute('data-prompt');
            if (prompt && !isResearching) {
                promptInput.value = prompt;
                promptInput.style.height = 'auto';
                promptInput.style.height = Math.min(promptInput.scrollHeight, 160) + 'px';
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    // Drawer toggles
    function openReportsDrawer() {
        closeHistoryDrawer();
        reportsDrawer.classList.remove('translate-x-full');
        drawerBackdrop.classList.remove('hidden');
        setTimeout(() => drawerBackdrop.classList.add('opacity-100'), 10);
    }

    function closeReportsDrawer() {
        reportsDrawer.classList.add('translate-x-full');
        checkBackdrop();
    }

    function openHistoryDrawer() {
        closeReportsDrawer();
        historyDrawer.classList.remove('-translate-x-full');
        drawerBackdrop.classList.remove('hidden');
        setTimeout(() => drawerBackdrop.classList.add('opacity-100'), 10);
    }

    function closeHistoryDrawer() {
        historyDrawer.classList.add('-translate-x-full');
        checkBackdrop();
    }

    function checkBackdrop() {
        setTimeout(() => {
            if (reportsDrawer.classList.contains('translate-x-full') && 
                historyDrawer.classList.contains('-translate-x-full')) {
                drawerBackdrop.classList.remove('opacity-100');
                drawerBackdrop.classList.add('hidden');
            }
        }, 150);
    }

    toggleDrawerBtn.addEventListener('click', openReportsDrawer);
    closeDrawerBtn.addEventListener('click', closeReportsDrawer);
    toggleHistoryBtn.addEventListener('click', openHistoryDrawer);
    closeHistoryBtn.addEventListener('click', closeHistoryDrawer);
    drawerBackdrop.addEventListener('click', () => {
        closeReportsDrawer();
        closeHistoryDrawer();
    });

    historySearch.addEventListener('input', () => {
        renderHistoryList();
    });

    // Report Drawer Search & Filter Tabs Listeners
    const clearReportSearchBtn = document.getElementById('clear-report-search-btn');

    if (reportSearch) {
        reportSearch.addEventListener('input', () => {
            if (clearReportSearchBtn) {
                if (reportSearch.value.trim().length > 0) {
                    clearReportSearchBtn.classList.remove('hidden');
                } else {
                    clearReportSearchBtn.classList.add('hidden');
                }
            }
            renderReportsList();
        });
        reportSearch.addEventListener('keyup', () => {
            renderReportsList();
        });
    }

    if (clearReportSearchBtn) {
        clearReportSearchBtn.addEventListener('click', () => {
            if (reportSearch) {
                reportSearch.value = '';
                clearReportSearchBtn.classList.add('hidden');
                renderReportsList();
                reportSearch.focus();
            }
        });
    }

    function updateFilterTabsUI() {
        filterTabs.forEach(t => {
            const f = t.getAttribute('data-filter');
            if (f === activeFilter) {
                t.className = 'filter-tab px-2.5 py-1 rounded-md bg-indigo-600 text-white font-semibold shadow-sm transition-all';
            } else {
                t.className = 'filter-tab px-2.5 py-1 rounded-md bg-slate-200/80 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all';
            }
        });
    }

    filterTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            activeFilter = tab.getAttribute('data-filter') || 'all';
            updateFilterTabsUI();
            renderReportsList();
        });
    });

    historyNewChatBtn.addEventListener('click', () => {
        closeHistoryDrawer();
        startNewThread();
    });

    if (closePreviewBtn) {
        closePreviewBtn.addEventListener('click', () => {
            if (previewModal) previewModal.classList.add('hidden');
        });
    }

    if (previewModal) {
        previewModal.addEventListener('click', (e) => {
            if (e.target === previewModal) {
                previewModal.classList.add('hidden');
            }
        });
    }

    clearAllHistoryBtn.addEventListener('click', () => {
        clearAllHistory();
    });

    // Reset Agent Session / New Thread
    resetSessionBtn.addEventListener('click', () => {
        startNewThread();
    });

    async function startNewThread() {
        try {
            await fetch('/api/reset/', { method: 'POST' });
        } catch (e) {}
        currentConversationId = null;
        lastReport = null;
        chatContainer.innerHTML = '';
        if (welcomeHero) welcomeHero.classList.remove('hidden');
        renderHistoryList();
        showToast('Fresh thread ready.', 'info');
    }

    // Fetch Initial Reports, Conversations & System Status
    fetchReports();
    fetchConversations();
    fetchStatus();

    async function fetchConversations() {
        try {
            const res = await fetch('/api/conversations/');
            const data = await res.json();
            if (data.status === 'success') {
                conversationsData = data.conversations || [];
                historyCountBadge.textContent = conversationsData.length;
                renderHistoryList();
            }
        } catch (err) {
            console.error('Error fetching conversations:', err);
        }
    }

    function renderHistoryList() {
        const query = (historySearch.value || '').toLowerCase().trim();
        let filtered = conversationsData;

        if (query) {
            filtered = filtered.filter(c => 
                (c.title || '').toLowerCase().includes(query) || 
                (c.preview || '').toLowerCase().includes(query)
            );
        }

        if (filtered.length === 0) {
            historyList.innerHTML = `
                <div class="text-center py-10 px-4">
                    <div class="w-10 h-10 mx-auto rounded-full bg-white/5 flex items-center justify-center text-slate-500 mb-2.5">
                        <i data-lucide="message-square-off" class="w-5 h-5"></i>
                    </div>
                    <p class="text-xs font-medium text-slate-400">No conversations found</p>
                    <p class="text-[11px] text-slate-500 mt-1">Start chatting to automatically record history</p>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        historyList.innerHTML = filtered.map(c => {
            const isActive = c.id === currentConversationId;
            const activeClass = isActive 
                ? 'bg-indigo-600/10 dark:bg-indigo-600/20 border-indigo-500/50 shadow-md shadow-indigo-500/10' 
                : 'bg-slate-100/70 dark:bg-white/5 border-slate-200/80 dark:border-white/5 hover:bg-slate-200/60 dark:hover:bg-white/10';

            // Format date
            let timeStr = '';
            if (c.updated_at) {
                try {
                    const d = new Date(c.updated_at);
                    timeStr = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' · ' +
                              d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                } catch (e) {
                    timeStr = c.updated_at;
                }
            }

            return `
                <div onclick="window.loadConversation('${escapeHtml(c.id)}')" 
                     class="group p-3 rounded-xl border ${activeClass} transition-all cursor-pointer flex items-start justify-between gap-2">
                    <div class="flex items-start gap-2.5 min-w-0 flex-1">
                        <div class="w-7 h-7 rounded-lg ${isActive ? 'bg-indigo-600 text-white' : 'bg-slate-200 dark:bg-white/5 text-slate-500 dark:text-slate-400'} flex items-center justify-center flex-shrink-0 mt-0.5">
                            <i data-lucide="message-square" class="w-3.5 h-3.5"></i>
                        </div>
                        <div class="min-w-0 flex-1">
                            <h4 class="text-xs font-semibold ${isActive ? 'text-indigo-600 dark:text-white' : 'text-slate-800 dark:text-slate-200'} truncate" title="${escapeHtml(c.title)}">
                                ${escapeHtml(c.title)}
                            </h4>
                            <div class="flex items-center gap-2 mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                                <span>${timeStr}</span>
                                <span>•</span>
                                <span>${c.message_count} msgs</span>
                            </div>
                        </div>
                    </div>
                    
                    <button onclick="window.deleteConversation(event, '${escapeHtml(c.id)}')" 
                            title="Delete thread" 
                            class="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-all flex-shrink-0">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    }

    window.loadConversation = async function(convId) {
        try {
            const res = await fetch(`/api/conversations/${convId}/`);
            const data = await res.json();
            if (data.status === 'success' && data.conversation) {
                const conv = data.conversation;
                currentConversationId = conv.id;
                lastReport = conv.last_report || null;

                if (welcomeHero) welcomeHero.classList.add('hidden');
                chatContainer.innerHTML = '';

                (conv.messages || []).forEach(msg => {
                    if (msg.role === 'user') {
                        appendUserMessage(msg.content);
                    } else if (msg.role === 'assistant') {
                        appendAgentResponse(msg.content, msg.is_saved, msg.saved_path);
                    }
                });

                closeHistoryDrawer();
                renderHistoryList();
                showToast('Loaded conversation thread', 'info');
            }
        } catch (e) {
            showToast('Failed to load conversation', 'error');
        }
    };

    window.deleteConversation = async function(event, convId) {
        event.stopPropagation();
        if (!confirm('Delete this conversation from history?')) return;
        try {
            const res = await fetch(`/api/conversations/${convId}/delete/`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                if (currentConversationId === convId) {
                    startNewThread();
                }
                fetchConversations();
                showToast('Conversation deleted', 'info');
            }
        } catch (e) {
            showToast('Unable to delete conversation', 'error');
        }
    };

    async function clearAllHistory() {
        if (!confirm('Clear all conversation history? This cannot be undone.')) return;
        try {
            const res = await fetch('/api/conversations/clear/', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                startNewThread();
                fetchConversations();
                showToast('All history cleared', 'info');
            }
        } catch (e) {
            showToast('Failed to clear history', 'error');
        }
    }

    async function fetchStatus() {
        try {
            const res = await fetch('/api/status/');
            const data = await res.json();
            if (data.status === 'online') {
                agentStatusPill.innerHTML = `
                    <span class="pulsing-dot mr-2"></span>
                    <span class="text-xs font-medium text-emerald-400">Agent Ready</span>
                    <span class="mx-2 text-slate-600">|</span>
                    <span class="text-xs text-indigo-300 font-mono">${data.model}</span>
                `;
            }
        } catch (e) {
            agentStatusPill.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-amber-400 mr-2"></span>
                <span class="text-xs font-medium text-amber-400">Local Mode</span>
            `;
        }
    }

    async function fetchReports() {
        try {
            const res = await fetch('/api/reports/');
            const data = await res.json();
            if (data.status === 'success') {
                reportsData = data.reports || [];
                reportsCountBadge.textContent = reportsData.length;
                drawerCountBadge.textContent = `${reportsData.length} files`;
                updateFilterTabsUI();
                renderReportsList();
            }
        } catch (err) {
            console.error('Error fetching reports:', err);
        }
    }

    function renderReportsList() {
        const query = (reportSearch && reportSearch.value ? reportSearch.value : '').toLowerCase().trim();
        let filtered = reportsData || [];

        // Format tab filter
        if (activeFilter === 'pdf') {
            filtered = filtered.filter(r => (r.format || '').toLowerCase() === 'pdf');
        } else if (activeFilter === 'docx' || activeFilter === 'word') {
            filtered = filtered.filter(r => ['docx', 'doc', 'word'].includes((r.format || '').toLowerCase()));
        } else if (activeFilter === 'md' || activeFilter === 'markdown') {
            filtered = filtered.filter(r => ['md', 'markdown'].includes((r.format || '').toLowerCase()));
        }

        // Search text filter
        if (query) {
            filtered = filtered.filter(r => 
                (r.filename || '').toLowerCase().includes(query) || 
                (r.topic || '').toLowerCase().includes(query) ||
                (r.format || '').toLowerCase().includes(query) ||
                (r.relpath || '').toLowerCase().includes(query)
            );
        }

        if (filtered.length === 0) {
            reportsList.innerHTML = `
                <div class="text-center py-12 px-4">
                    <div class="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 dark:text-slate-500 mb-3">
                        <i data-lucide="folder-search" class="w-6 h-6"></i>
                    </div>
                    <p class="text-sm font-medium text-slate-700 dark:text-slate-400">No matching reports found</p>
                    <p class="text-xs text-slate-500 mt-1">Try clearing search or choosing another format filter</p>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        reportsList.innerHTML = filtered.map(report => {
            const extColor = getBadgeClass(report.format);
            const iconName = getIconName(report.format);

            return `
                <div class="glass-panel p-3.5 rounded-xl hover-lift border border-slate-200/80 dark:border-white/5 hover:border-indigo-500/40 transition-all flex flex-col gap-2.5">
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-2.5 min-w-0">
                            <div class="w-8 h-8 rounded-lg ${extColor.bg} flex items-center justify-center flex-shrink-0 text-white shadow-sm">
                                <i data-lucide="${iconName}" class="w-4 h-4"></i>
                            </div>
                            <div class="min-w-0">
                                <h4 class="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate" title="${escapeHtml(report.filename)}">
                                    ${escapeHtml(report.filename)}
                                </h4>
                                <div class="flex items-center gap-2 mt-0.5">
                                    <span class="text-[10px] font-medium px-1.5 py-0.5 rounded ${extColor.tag}">
                                        ${report.format.toUpperCase()}
                                    </span>
                                    <span class="text-[11px] text-slate-500 dark:text-slate-400 truncate">${report.topic}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex items-center justify-between pt-2 border-t border-slate-200/80 dark:border-white/5 text-[11px] text-slate-500 dark:text-slate-400">
                        <span>${report.size_human} · ${report.modified_formatted}</span>
                        <div class="flex items-center gap-1.5">
                            ${report.format === 'md' ? `
                                <button onclick="window.previewReport('${encodeURIComponent(report.relpath)}')" 
                                        class="px-2 py-1 rounded-md bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors flex items-center gap-1">
                                    <i data-lucide="eye" class="w-3 h-3"></i>
                                    <span>Preview</span>
                                </button>
                            ` : ''}
                            <a href="/api/reports/download/${encodeURIComponent(report.relpath)}" 
                               download
                               class="px-2.5 py-1 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white transition-all flex items-center gap-1 shadow-sm font-medium">
                                <i data-lucide="download" class="w-3 h-3"></i>
                                <span>Get</span>
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    }

    function getBadgeClass(format) {
        switch (format) {
            case 'pdf':
                return { bg: 'bg-rose-500/20 text-rose-400', tag: 'bg-rose-500/10 text-rose-300 border border-rose-500/20' };
            case 'docx':
            case 'doc':
                return { bg: 'bg-blue-500/20 text-blue-400', tag: 'bg-blue-500/10 text-blue-300 border border-blue-500/20' };
            case 'md':
                return { bg: 'bg-violet-500/20 text-violet-400', tag: 'bg-violet-500/10 text-violet-300 border border-violet-500/20' };
            default:
                return { bg: 'bg-slate-500/20 text-slate-400', tag: 'bg-slate-500/10 text-slate-300 border border-slate-500/20' };
        }
    }

    function getIconName(format) {
        switch (format) {
            case 'pdf': return 'file-text';
            case 'docx': case 'doc': return 'file-code';
            case 'md': return 'file-spreadsheet';
            default: return 'file';
        }
    }

    // Window global for previewing reports
    window.previewReport = async function(relpath) {
        try {
            const res = await fetch(`/api/reports/preview/${relpath}`);
            const data = await res.json();
            if (data.status === 'success' && data.is_text) {
                previewTitle.textContent = data.filename;
                previewContent.innerHTML = marked.parse(data.content);
                previewDownloadBtn.href = `/api/reports/download/${relpath}`;
                previewModal.classList.remove('hidden');
                if (window.lucide) lucide.createIcons();
            } else {
                window.location.href = `/api/reports/download/${relpath}`;
            }
        } catch (e) {
            showToast('Unable to preview file', 'error');
        }
    };

    // Chat Submission Form
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const prompt = promptInput.value.trim();
        if (!prompt || isResearching) return;

        // Hide welcome hero if first message
        if (welcomeHero) welcomeHero.classList.add('hidden');

        // Clear input and restore height
        promptInput.value = '';
        promptInput.style.height = 'auto';

        // Append User Message Bubble
        appendUserMessage(prompt);

        // Append Loading State with Animated Telemetry
        const loaderId = appendAgentLoader(prompt);

        isResearching = true;
        sendBtn.disabled = true;
        sendBtn.classList.add('opacity-50', 'cursor-not-allowed');

        try {
            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    last_report: lastReport,
                    conversation_id: currentConversationId
                })
            });

            const data = await response.json();
            stopResearchProgress();

            if (data.status === 'success') {
                const responseText = data.response;
                const stripped = responseText.trim();

                // If not a save confirmation, update lastReport
                if (!stripped.startsWith('SAVED:') && !stripped.startsWith('SAVE_FAILED:')) {
                    lastReport = responseText;
                }

                // Update current conversation id and refresh history list
                if (data.conversation_id) {
                    currentConversationId = data.conversation_id;
                    fetchConversations();
                }

                // Remove loader and append agent response
                removeElement(loaderId);
                appendAgentResponse(responseText, data.is_saved, data.saved_path);

                // If saved, refresh reports vault
                if (data.is_saved) {
                    fetchReports();
                    showToast('Document saved to vault!', 'success');
                }
            } else {
                removeElement(loaderId);
                appendErrorMessage(data.message || 'An error occurred during agent execution.');
            }
        } catch (err) {
            stopResearchProgress();
            removeElement(loaderId);
            appendErrorMessage(err.message || 'Network communication error.');
        } finally {
            isResearching = false;
            sendBtn.disabled = false;
            sendBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            promptInput.focus();
        }
    });

    function appendUserMessage(text) {
        const msg = document.createElement('div');
        msg.className = 'flex justify-end gap-2 sm:gap-3 mb-4 sm:mb-6 animate-fadeIn';
        msg.innerHTML = `
            <div class="max-w-[88%] sm:max-w-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-2xl rounded-tr-sm px-3.5 sm:px-5 py-2.5 sm:py-3.5 shadow-lg shadow-indigo-500/10 text-xs sm:text-sm leading-relaxed font-normal">
                ${escapeHtml(text)}
            </div>
            <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-indigo-300 flex-shrink-0 text-[10px] sm:text-xs font-semibold">
                You
            </div>
        `;
        chatContainer.appendChild(msg);
        scrollToBottom();
    }

    function appendAgentLoader(userPrompt) {
        const loaderId = 'loader-' + Date.now();
        const loader = document.createElement('div');
        loader.id = loaderId;
        loader.className = 'flex gap-2 sm:gap-4 mb-4 sm:mb-6 animate-fadeIn';

        loader.innerHTML = `
            <div class="w-7 h-7 sm:w-9 sm:h-9 rounded-lg sm:rounded-xl bg-gradient-to-br from-indigo-500 to-violet-700 flex items-center justify-center text-white flex-shrink-0 shadow-lg shadow-indigo-500/20 mt-0.5">
                <i data-lucide="bot" class="w-4 h-4 sm:w-5 sm:h-5"></i>
            </div>
            <div class="flex-1 glass-panel rounded-2xl rounded-tl-sm p-3.5 sm:p-5 border border-indigo-500/20 max-w-2xl min-w-0">
                <!-- Universal Header: Quantum Core + Universal Status + Wave + Timer -->
                <div class="flex items-center justify-between pb-2.5 sm:pb-3 border-b border-slate-200/80 dark:border-white/5">
                    <div class="flex items-center gap-2.5 sm:gap-3.5 min-w-0">
                        <!-- Quantum Core Animation -->
                        <div class="quantum-core flex-shrink-0">
                            <div class="quantum-ring quantum-ring-1"></div>
                            <div class="quantum-ring quantum-ring-2"></div>
                            <div class="quantum-nucleus"></div>
                        </div>
                        <div class="min-w-0">
                            <div class="flex items-center gap-1.5 sm:gap-2">
                                <span class="shimmer-text text-[11px] sm:text-xs font-bold tracking-wider uppercase truncate">AI Processing</span>
                                <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping flex-shrink-0"></span>
                            </div>
                            <p class="text-[10px] sm:text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate" id="phase-status-text">Understanding instructions...</p>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-2 sm:gap-2.5 flex-shrink-0">
                        <!-- Neural Frequency Equalizer Wave -->
                        <div class="neural-wave hidden sm:flex" title="Active computation">
                            <div class="neural-bar"></div>
                            <div class="neural-bar"></div>
                            <div class="neural-bar"></div>
                            <div class="neural-bar"></div>
                            <div class="neural-bar"></div>
                        </div>
                        <!-- Elapsed Timer Badge -->
                        <div class="px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full bg-slate-100 dark:bg-white/5 text-[10px] sm:text-[11px] font-mono text-cyan-600 dark:text-cyan-300 border border-slate-200 dark:border-white/10 flex items-center gap-1">
                            <span id="elapsed-timer">0s</span>
                        </div>
                    </div>
                </div>

                <!-- Universal Thought Formulation Stream (Skeleton Waves) -->
                <div class="py-3 flex flex-col gap-2">
                    <div class="skeleton-line w-[85%]"></div>
                    <div class="skeleton-line w-[65%]"></div>
                    <div class="skeleton-line w-[40%]"></div>
                </div>

                <!-- Universal Capability Badges -->
                <div class="pt-2 border-t border-slate-200/80 dark:border-white/5 flex items-center justify-between text-[10px] sm:text-[11px] text-slate-500 dark:text-slate-400">
                    <div class="flex items-center gap-2 sm:gap-3">
                        <span class="flex items-center gap-1">
                            <i data-lucide="cpu" class="w-3 h-3 text-indigo-500 dark:text-indigo-400"></i>
                            <span id="loader-mode-badge">Active Reasoning</span>
                        </span>
                        <span class="text-slate-300 dark:text-slate-700">•</span>
                        <span class="flex items-center gap-1">
                            <i data-lucide="wrench" class="w-3 h-3 text-violet-500 dark:text-violet-400"></i>
                            <span>Tools</span>
                        </span>
                    </div>
                    <span class="text-[9px] sm:text-[10px] text-slate-400 dark:text-slate-500 font-mono">stream active</span>
                </div>
            </div>
        `;

        chatContainer.appendChild(loader);
        if (window.lucide) lucide.createIcons();
        scrollToBottom();

        startResearchProgress();
        return loaderId;
    }

    function startResearchProgress() {
        currentSeconds = 0;
        const timerElem = document.getElementById('elapsed-timer');
        const statusText = document.getElementById('phase-status-text');
        const modeBadge = document.getElementById('loader-mode-badge');

        // Universal progression that fits ANY task (web, directory, files, math, Q&A)
        const universalPhases = [
            { sec: 0, text: "Understanding instructions and planning actions...", mode: "Intent Analysis" },
            { sec: 3, text: "Executing operations with active tools & environment...", mode: "Tool Execution" },
            { sec: 8, text: "Processing data and cross-referencing context...", mode: "Context Synthesis" },
            { sec: 14, text: "Synthesizing output and preparing response...", mode: "Response Formulation" },
        ];

        progressTimer = setInterval(() => {
            currentSeconds++;
            if (timerElem) timerElem.textContent = `${currentSeconds}s`;

            if (currentSeconds === 3 && statusText && modeBadge) {
                statusText.textContent = universalPhases[1].text;
                modeBadge.textContent = universalPhases[1].mode;
            } else if (currentSeconds === 8 && statusText && modeBadge) {
                statusText.textContent = universalPhases[2].text;
                modeBadge.textContent = universalPhases[2].mode;
            } else if (currentSeconds === 14 && statusText && modeBadge) {
                statusText.textContent = universalPhases[3].text;
                modeBadge.textContent = universalPhases[3].mode;
            }
        }, 1000);
    }

    function stopResearchProgress() {
        if (progressTimer) {
            clearInterval(progressTimer);
            progressTimer = null;
        }
    }

    function parseReferencesAndCleanContent(rawContent) {
        let content = rawContent || '';
        let sources = [];

        // Remove the "Reply 'save as ...'" footer line if present
        content = content.replace(/\n*Reply\s*['"]?save as\s*<format>['"]?.*$/i, '');
        content = content.replace(/\n*Reply\s*['"]?save as\s*['"]?.*if you want this saved.*$/i, '');
        content = content.replace(/\n*Reply\s*['"]?save as\s*['"]?.*$/i, '');

        // Match ## References or References: section at end
        const refMatch = content.match(/(?:^|\n)(?:#{1,3}\s*References|References:)([\s\S]*)$/i);
        if (refMatch) {
            const refSection = refMatch[1];
            content = content.substring(0, refMatch.index).trim();

            const lines = refSection.split('\n');
            lines.forEach(line => {
                const trimmed = line.trim();
                if (!trimmed) return;

                const urlMatch = trimmed.match(/(https?:\/\/[^\s\)\>\]]+)/i);
                if (urlMatch) {
                    let url = urlMatch[1].replace(/[.,;:\)\]>]+$/, '');
                    let title = '';
                    const titleMatch = trimmed.match(/\[([^\]]+)\]/);
                    if (titleMatch) {
                        title = titleMatch[1].trim();
                    } else {
                        title = trimmed.replace(/^[\d+.\-*#\s]+/, '').split('http')[0].replace(/[-:]\s*$/, '').trim();
                    }

                    try {
                        const parsedUrl = new URL(url);
                        const domain = parsedUrl.hostname.replace(/^www\./, '');
                        if (!title || title.length < 2) {
                            title = domain;
                        }
                        sources.push({
                            title: title,
                            url: url,
                            domain: domain,
                            favicon: `https://www.google.com/s2/favicons?domain=${domain}&sz=32`
                        });
                    } catch (e) {}
                }
            });
        }

        // Deduplicate sources by URL
        const uniqueSources = [];
        const seenUrls = new Set();
        sources.forEach(s => {
            if (!seenUrls.has(s.url)) {
                seenUrls.add(s.url);
                uniqueSources.push(s);
            }
        });

        return {
            cleanedContent: content,
            sources: uniqueSources
        };
    }

    window.toggleSources = function(trayId) {
        const tray = document.getElementById(trayId);
        const chevron = document.getElementById('chevron-' + trayId);
        if (!tray) return;
        if (tray.classList.contains('hidden')) {
            tray.classList.remove('hidden');
            if (chevron) chevron.style.transform = 'rotate(180deg)';
        } else {
            tray.classList.add('hidden');
            if (chevron) chevron.style.transform = 'rotate(0deg)';
        }
    };

    function appendAgentResponse(content, isSaved, savedPath) {
        const msg = document.createElement('div');
        msg.className = 'flex gap-2 sm:gap-4 mb-6 sm:mb-8 animate-fadeIn';

        const { cleanedContent, sources } = parseReferencesAndCleanContent(content);

        let parsedHtml = '';
        if (window.marked) {
            parsedHtml = marked.parse(cleanedContent);
        } else {
            parsedHtml = `<p class="whitespace-pre-wrap">${escapeHtml(cleanedContent)}</p>`;
        }

        const msgId = 'msg-' + Date.now();
        const sourcesId = 'sources-' + Date.now();

        // Check if saved
        let saveBanner = '';
        if (isSaved && savedPath) {
            const filename = savedPath.split('/').pop();
            saveBanner = `
                <div class="mb-3.5 sm:mb-4 p-3 sm:p-4 rounded-xl bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-transparent border border-emerald-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div class="flex items-center gap-2.5 sm:gap-3 min-w-0">
                        <div class="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0">
                            <i data-lucide="check-circle" class="w-4 h-4 sm:w-5 sm:h-5"></i>
                        </div>
                        <div class="min-w-0">
                            <h4 class="text-xs font-semibold text-white">Report Successfully Saved</h4>
                            <p class="text-[10px] sm:text-[11px] text-slate-400 font-mono truncate">${escapeHtml(savedPath)}</p>
                        </div>
                    </div>
                    <a href="/api/reports/download/${encodeURIComponent(savedPath)}" 
                       download
                       class="px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center gap-1.5 sm:gap-2 shadow-lg shadow-emerald-500/20 transition-all flex-shrink-0">
                        <i data-lucide="download" class="w-3.5 h-3.5 sm:w-4 sm:h-4"></i>
                        <span>Download</span>
                    </a>
                </div>
            `;
        }

        // Generate Perplexity-style Sources Pill (Matching Image 2)
        let sourcesPillHtml = '';
        if (sources && sources.length > 0) {
            const previewFavicons = sources.slice(0, 4);
            const faviconsHtml = previewFavicons.map(s => 
                `<img src="${s.favicon}" alt="${s.domain}" class="w-4 h-4 rounded-full border border-slate-900 dark:border-[#131722] bg-slate-800 object-cover flex-shrink-0" onerror="this.style.display='none'" />`
            ).join('');

            const sourcesCardsHtml = sources.map((s, idx) => `
                <a href="${s.url}" target="_blank" rel="noopener noreferrer" 
                   class="source-card p-2 sm:p-2.5 rounded-xl bg-slate-100/90 dark:bg-white/5 hover:bg-slate-200/90 dark:hover:bg-white/10 border border-slate-200/90 dark:border-white/5 flex flex-col justify-between gap-1.5 group/card transition-all text-left">
                    <div class="flex items-center gap-1.5 sm:gap-2 min-w-0">
                        <img src="${s.favicon}" class="w-3.5 h-3.5 rounded-sm object-contain flex-shrink-0" onerror="this.style.display='none'" />
                        <span class="text-[10px] font-medium text-slate-500 dark:text-slate-400 truncate">${s.domain}</span>
                        <span class="text-[9px] text-slate-400 dark:text-slate-500 ml-auto font-mono">#${idx + 1}</span>
                    </div>
                    <h5 class="text-xs font-medium text-slate-800 dark:text-slate-200 group-hover/card:text-indigo-600 dark:group-hover/card:text-indigo-300 line-clamp-2 leading-snug">
                        ${escapeHtml(s.title)}
                    </h5>
                </a>
            `).join('');

            sourcesPillHtml = `
                <div class="sources-wrapper mb-3 sm:mb-4">
                    <!-- Pill Button matching Screenshot 2 -->
                    <button type="button" 
                            onclick="window.toggleSources('${sourcesId}')" 
                            class="source-pill inline-flex items-center gap-2 sm:gap-2.5 px-3 sm:px-3.5 py-1.5 rounded-full cursor-pointer select-none text-xs">
                        <div class="flex items-center -space-x-1.5 overflow-hidden">
                            ${faviconsHtml}
                        </div>
                        <span class="text-[11px] sm:text-xs font-semibold tracking-wide">${sources.length} web page${sources.length > 1 ? 's' : ''}</span>
                        <i data-lucide="chevron-down" id="chevron-${sourcesId}" class="w-3.5 h-3.5 text-slate-400 transition-transform duration-200"></i>
                    </button>

                    <!-- Expandable Sources Tray -->
                    <div id="${sourcesId}" class="hidden mt-2.5 sm:mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 p-2.5 sm:p-3 rounded-2xl bg-slate-100/80 dark:bg-slate-900/60 border border-slate-200 dark:border-white/5 animate-fadeIn">
                        ${sourcesCardsHtml}
                    </div>
                </div>
            `;
        }

        msg.innerHTML = `
            <div class="w-7 h-7 sm:w-9 sm:h-9 rounded-lg sm:rounded-xl bg-gradient-to-br from-indigo-500 to-violet-700 flex items-center justify-center text-white flex-shrink-0 shadow-lg shadow-indigo-500/20 mt-0.5">
                <i data-lucide="bot" class="w-4 h-4 sm:w-5 sm:h-5"></i>
            </div>
            <div class="flex-1 glass-panel rounded-2xl rounded-tl-sm p-3.5 sm:p-6 border border-slate-200/80 dark:border-white/5 max-w-4xl min-w-0" id="${msgId}">
                ${saveBanner}
                ${sourcesPillHtml}
                
                <div class="prose-report">
                    ${parsedHtml}
                </div>

                <!-- Quick Action Bar -->
                <div class="mt-4 sm:mt-6 pt-3 sm:pt-4 border-t border-slate-200/80 dark:border-white/5 flex flex-wrap items-center justify-between gap-2 sm:gap-3 text-xs">
                    <div class="flex items-center gap-1.5 sm:gap-2 text-slate-500 dark:text-slate-400">
                        <i data-lucide="sparkles" class="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400"></i>
                        <span class="text-[10px] sm:text-[11px]">Save Format:</span>
                    </div>
                    <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <button onclick="window.sendSaveCommand('save as pdf')" 
                                class="px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-rose-500/10 hover:text-rose-600 dark:hover:text-rose-300 hover:border-rose-500/40 border border-slate-200/80 dark:border-white/5 text-slate-700 dark:text-slate-300 transition-all flex items-center gap-1 sm:gap-1.5 text-[11px] sm:text-xs font-medium">
                            <i data-lucide="file-text" class="w-3.5 h-3.5 text-rose-500"></i>
                            <span class="hidden sm:inline">Save as </span><span>PDF</span>
                        </button>
                        <button onclick="window.sendSaveCommand('save as docx')" 
                                class="px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-blue-500/10 hover:text-blue-600 dark:hover:text-blue-300 hover:border-blue-500/40 border border-slate-200/80 dark:border-white/5 text-slate-700 dark:text-slate-300 transition-all flex items-center gap-1 sm:gap-1.5 text-[11px] sm:text-xs font-medium">
                            <i data-lucide="file-code" class="w-3.5 h-3.5 text-blue-500"></i>
                            <span class="hidden sm:inline">Save as </span><span>Word</span>
                        </button>
                        <button onclick="window.sendSaveCommand('save as markdown')" 
                                class="px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-violet-500/10 hover:text-violet-600 dark:hover:text-violet-300 hover:border-violet-500/40 border border-slate-200/80 dark:border-white/5 text-slate-700 dark:text-slate-300 transition-all flex items-center gap-1 sm:gap-1.5 text-[11px] sm:text-xs font-medium">
                            <i data-lucide="file-spreadsheet" class="w-3.5 h-3.5 text-violet-500"></i>
                            <span class="hidden sm:inline">Save as </span><span>MD</span>
                        </button>
                        <button onclick="window.copyReportText('${msgId}')" 
                                class="px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white border border-slate-200/80 dark:border-white/5 transition-all flex items-center gap-1 sm:gap-1.5 text-[11px] sm:text-xs font-medium">
                            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                            <span>Copy</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        chatContainer.appendChild(msg);
        if (window.lucide) lucide.createIcons();
        scrollToBottom();
    }

    function appendErrorMessage(errorText) {
        const msg = document.createElement('div');
        msg.className = 'flex gap-2 sm:gap-4 mb-4 sm:mb-6 animate-fadeIn';
        msg.innerHTML = `
            <div class="w-7 h-7 sm:w-9 sm:h-9 rounded-lg sm:rounded-xl bg-rose-500/20 text-rose-500 border border-rose-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <i data-lucide="alert-triangle" class="w-4 h-4 sm:w-5 sm:h-5"></i>
            </div>
            <div class="flex-1 glass-panel rounded-2xl rounded-tl-sm p-3.5 sm:p-4 border border-rose-200 dark:border-rose-500/20 max-w-2xl bg-rose-50/70 dark:bg-rose-950/20 min-w-0">
                <h4 class="text-xs font-semibold text-rose-700 dark:text-rose-300 mb-1">Execution Notice</h4>
                <p class="text-xs text-rose-600 dark:text-rose-200/80 leading-relaxed">${escapeHtml(errorText)}</p>
            </div>
        `;
        chatContainer.appendChild(msg);
        if (window.lucide) lucide.createIcons();
        scrollToBottom();
    }

    // Save helper called from quick buttons
    window.sendSaveCommand = function(cmd) {
        if (isResearching) return;
        promptInput.value = cmd;
        chatForm.dispatchEvent(new Event('submit'));
    };

    // Copy text helper
    window.copyReportText = function(msgId) {
        const elem = document.getElementById(msgId);
        if (!elem) return;
        const text = elem.querySelector('.prose-report').innerText;
        navigator.clipboard.writeText(text).then(() => {
            showToast('Report copied to clipboard!', 'success');
        });
    };

    function showToast(text, type = 'info') {
        const toast = document.createElement('div');
        const color = type === 'success' ? 'bg-emerald-600' : type === 'error' ? 'bg-rose-600' : 'bg-indigo-600';
        toast.className = `fixed bottom-6 right-6 ${color} text-white px-4 py-2.5 rounded-xl shadow-2xl text-xs font-medium z-50 flex items-center gap-2 animate-bounce`;
        toast.innerHTML = `<span>${escapeHtml(text)}</span>`;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        setTimeout(() => {
            const anchor = document.getElementById('chat-bottom-anchor');
            if (anchor) {
                anchor.scrollIntoView({ behavior: 'smooth', block: 'end' });
            } else {
                const target = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
                window.scrollTo({
                    top: target + 300,
                    behavior: 'smooth'
                });
            }
        }, 60);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
