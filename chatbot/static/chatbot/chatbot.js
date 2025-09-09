(function () {
    // DOM Elements
    const chatLog = document.getElementById('chat-log');
    const form = document.getElementById('chat-form');
    const questionEl = document.getElementById('question');
    const sendBtn = document.getElementById('send-btn');
    const progressIndicator = document.getElementById('progress-indicator');
    const stepsEl = document.getElementById('progress-steps');
    const limitsMinuteEl = document.getElementById('limits-minute');
    const limitsDayEl = document.getElementById('limits-day');
    const chatStatus = document.getElementById('chat-status');
    
    // Check if this is the first visit and show welcome message
    const isFirstVisit = !localStorage.getItem('chatbot_visited');
    if (isFirstVisit && chatLog) {
        localStorage.setItem('chatbot_visited', 'true');
        setTimeout(() => addMessage('assistant', '👋 Hola, soy tu Abogado Virtual. ¿En qué puedo ayudarte hoy?'), 500);
    }
    
    // Auto-resize textarea
    function autoResizeTextarea() {
        questionEl.style.height = 'auto';
        questionEl.style.height = (questionEl.scrollHeight) + 'px';
        if (questionEl.scrollHeight > 120) {
            questionEl.style.overflowY = 'auto';
        } else {
            questionEl.style.overflowY = 'hidden';
        }
    }
    
    if (questionEl) {
        questionEl.addEventListener('input', autoResizeTextarea);
        
        // Enter key sends message, Shift+Enter for new line
        questionEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (questionEl.value.trim()) {
                    form.dispatchEvent(new Event('submit'));
                }
            }
        });
    }

    // Get CSRF token
    function csrftoken() {
        const name = 'csrftoken=';
        const cookies = document.cookie.split(';');
        for (let c of cookies) {
            c = c.trim();
            if (c.startsWith(name)) return decodeURIComponent(c.substring(name.length));
        }
        return '';
    }

    // Add message to chat
    function addMessage(role, text) {
        const wrapper = document.createElement('div');
        wrapper.className = `message ${role}`;
        
        // Create avatar with icon
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const avatarIcon = document.createElement('i');
        
        if (role === 'assistant') {
            avatarIcon.className = 'bi bi-robot';
        } else {
            avatarIcon.className = 'bi bi-person';
        }
        
        avatar.appendChild(avatarIcon);
        
        // Create content container
        const content = document.createElement('div');
        content.className = 'content';
        
        // Create message bubble
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.textContent = text;
        
        // Create metadata (timestamp)
        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Append everything
        content.appendChild(bubble);
        content.appendChild(meta);
        wrapper.appendChild(avatar);
        wrapper.appendChild(content);
        
        // Add to chat log with animation delay
        chatLog.appendChild(wrapper);
        
        // Scroll to bottom with smooth animation
        smoothScrollToBottom();
    }
    
    // Smooth scroll to bottom of chat with improved visibility of both history and input
    function smoothScrollToBottom() {
        if (!chatLog) return;
        
        const scrollHeight = chatLog.scrollHeight;
        
        // Check if we're already at the bottom (within a small threshold)
        const isNearBottom = chatLog.scrollTop >= (scrollHeight - chatLog.clientHeight - 50);
        
        // Always do a smooth scroll for better UX
        try {
            // Use native smooth scrolling when possible
            chatLog.scrollTo({
                top: scrollHeight,
                behavior: isNearBottom ? 'auto' : 'smooth'
            });
            
            // Double check after animation has time to complete
            setTimeout(() => {
                if (chatLog.scrollTop < scrollHeight - 20) {
                    chatLog.scrollTop = scrollHeight;
                }
            }, 350);
        } catch (error) {
            // Fallback for browsers without scrollTo support
            chatLog.scrollTop = scrollHeight;
        }
    }

    // Toggle loading state
    function setLoading(loading) {
        sendBtn.disabled = loading;
        progressIndicator.classList.toggle('d-none', !loading);
        
        // Update status indicator
        if (chatStatus) {
            if (loading) {
                chatStatus.className = 'badge rounded-pill bg-warning';
                chatStatus.innerHTML = '<span class="status-dot"></span> Procesando';
            } else {
                chatStatus.className = 'badge rounded-pill bg-success';
                chatStatus.innerHTML = '<span class="status-dot"></span> Activo';
            }
        }
    }

    // Reset progress steps
    function resetSteps() {
        stepsEl.querySelectorAll('li').forEach(li => {
            li.classList.remove('active', 'done');
        });
    }

    // Mark progress step as active/done
    function markStep(state) {
        const order = [
            'queued',
            'gathering_context',
            'calling_llm',
            'streaming_answer',
            'done'
        ];
        let reached = true;
        stepsEl.querySelectorAll('li').forEach(li => {
            const s = li.getAttribute('data-step');
            if (reached) li.classList.add('active');
            if (s === state) reached = false; // Después de este, los siguientes no marcados aún
            if (order.indexOf(s) < order.indexOf(state)) li.classList.add('done');
        });
    }

    // Poll for progress updates
    async function pollProgress(key) {
        try {
            const url = new URL(window.location.origin + '/chatbot/api/progress/');
            url.searchParams.set('key', key);
            const res = await fetch(url);
            if (!res.ok) return;
            
            const data = await res.json();
            if (data.status === 'ok') {
                const state = data.progress.state;
                markStep(state);
                if (state && state !== 'done' && state !== 'error') {
                    setTimeout(() => pollProgress(key), 800);
                }
            }
        } catch (e) {
            console.error('poll error', e);
        }
    }

    // Form submission
    form?.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const question = questionEl.value.trim();
        if (!question) return;
        
        // Add user message
        addMessage('user', question);
        
        // Clear input and reset height
        questionEl.value = '';
        questionEl.style.height = 'auto';
        
        // Focus back on input
        questionEl.focus();
        
        // Reset progress steps and show loading
        resetSteps();
        setLoading(true);
        
        try {
            // Send request to API
            const res = await fetch('/chatbot/api/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken(),
                },
                body: JSON.stringify({ question }),
            });
            
            const data = await res.json();
            
            // Handle rate limiting
            if (res.status === 429 || data.status === 'rate_limited') {
                addMessage('assistant', data.message || 'Has alcanzado el límite de consultas. Por favor, espera un momento.');
                
                // Show error animation
                const statusEl = document.createElement('div');
                statusEl.className = 'alert alert-warning my-3 animate__animated animate__fadeIn';
                statusEl.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i> Límite de consultas alcanzado';
                chatLog.appendChild(statusEl);
                
                // Update limits
                limitsMinuteEl.textContent = `Por minuto: ${data?.limits?.minute_left ?? '—'}`;
                limitsDayEl.textContent = `Por día: ${data?.limits?.day_left ?? '—'}`;
                
                // Scroll to bottom
                smoothScrollToBottom();
                setLoading(false);
                return;
            }
            
            // Handle general errors
            if (!res.ok || data.status !== 'ok') {
                addMessage('assistant', data.message || 'Lo siento, ha ocurrido un error. Por favor, intenta nuevamente.');
                setLoading(false);
                return;
            }
            
            // Poll progress if available
            if (data.progress_key) {
                pollProgress(data.progress_key);
            }
            
            // Update limits
            limitsMinuteEl.textContent = `Por minuto: ${data?.limits?.minute_left ?? '—'}`;
            limitsDayEl.textContent = `Por día: ${data?.limits?.day_left ?? '—'}`;
            
            // Add assistant message with typing effect for longer responses
            if (data.message && data.message.length > 100) {
                const typingDelay = Math.min(800, data.message.length * 2);
                setTimeout(() => {
                    addMessage('assistant', data.message);
                }, typingDelay);
            } else {
                addMessage('assistant', data.message || 'No pude procesar tu consulta. Por favor, intenta nuevamente.');
            }
            
        } catch (e) {
            console.error(e);
            addMessage('assistant', 'Error de conexión. Por favor, verifica tu conexión a internet e intenta nuevamente.');
        } finally {
            setLoading(false);
        }
    });
    
    // Add scroll-to-bottom button when user scrolls up
    function initScrollToBottomButton() {
        // Create button element if it doesn't exist
        if (!document.getElementById('scroll-to-bottom')) {
            const scrollButton = document.createElement('button');
            scrollButton.id = 'scroll-to-bottom';
            scrollButton.className = 'scroll-bottom-btn';
            scrollButton.innerHTML = '<i class="bi bi-arrow-down"></i> Ver nuevos mensajes';
            scrollButton.setAttribute('aria-label', 'Desplazar al final del chat');
            scrollButton.style.display = 'none';
            document.body.appendChild(scrollButton); // Attach to body to ensure it's always visible
            
            // Add click event with improved scrolling
            scrollButton.addEventListener('click', () => {
                smoothScrollToBottom();
                // Briefly highlight the input field to show where focus is
                if (questionEl) {
                    questionEl.classList.add('highlight-input');
                    setTimeout(() => {
                        questionEl.classList.remove('highlight-input');
                        questionEl.focus();
                    }, 800);
                }
            });
            
            // Enhanced scroll monitoring
            if (chatLog) {
                // Monitor scroll position to show/hide button
                chatLog.addEventListener('scroll', () => {
                    // Check if we're near the bottom (with a margin for usability)
                    const isNearBottom = chatLog.scrollTop >= (chatLog.scrollHeight - chatLog.clientHeight - 80);
                    
                    // Only show the button when we're not near the bottom
                    if (!isNearBottom) {
                        scrollButton.style.display = 'flex';
                    } else {
                        scrollButton.style.display = 'none';
                    }
                });
                
                // Also check when new content might be added
                const observer = new MutationObserver(() => {
                    const isNearBottom = chatLog.scrollTop >= (chatLog.scrollHeight - chatLog.clientHeight - 80);
                    if (!isNearBottom) {
                        scrollButton.style.display = 'flex';
                    }
                });
                
                observer.observe(chatLog, { childList: true, subtree: true });
            }
        }
    }
    
    // Handle viewport changes (like keyboard appearing on mobile)
    function handleViewportChanges() {
        let lastHeight = window.innerHeight;
        
        window.addEventListener('resize', () => {
            // If height decreases significantly (keyboard appearing)
            if (window.innerHeight < lastHeight - 150) {
                // Small delay to let the keyboard fully appear
                setTimeout(() => {
                    // Ensure input is visible
                    questionEl.scrollIntoView({ behavior: 'smooth' });
                }, 300);
            }
            lastHeight = window.innerHeight;
        });
    }
    
    // Initialize - Add initial focus to textarea and setup helpers
    if (questionEl) {
        setTimeout(() => {
            questionEl.focus();
            initScrollToBottomButton();
            handleViewportChanges();
        }, 500);
    }
    
    // Add keyboard shortcut (Alt+N) to focus on the textarea
    document.addEventListener('keydown', (e) => {
        if (e.altKey && e.key === 'n' && questionEl) {
            e.preventDefault();
            questionEl.focus();
        }
    });
})();