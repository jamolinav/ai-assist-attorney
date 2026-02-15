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
    const cardBody = document.querySelector('.card-body');
    
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

    // Add message to chat with enhanced animations and effects
    // ...existing code...

    // Add message to chat with enhanced animations and effects, interpret HTML from server
    function addMessage(role, text) {
        const wrapper = document.createElement('div');
        wrapper.className = `message ${role}`;
        wrapper.classList.add(role === 'assistant' ? 'glass-message' : 'user-message');

        // Create avatar with icon
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const avatarIcon = document.createElement('i');
        avatarIcon.className = role === 'assistant' ? 'bi bi-robot' : 'bi bi-person';
        avatar.appendChild(avatarIcon);

        // Create content container
        const content = document.createElement('div');
        content.className = 'content';

        // Create message bubble with animation delay
        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        // Interpret HTML from server in assistant messages
        if (role === 'assistant') {
            bubble.innerHTML = text // `<strong>${author}:</strong> ${text}`;
        } else {
            bubble.textContent = text; // User messages as plain text
        }

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

        // Add subtle entrance animation
        setTimeout(() => {
            wrapper.classList.add('message-visible');
        }, 50);

        // Scroll to bottom with smooth animation
        smoothScrollToBottom();
    }
    
    // Enhanced smooth scroll to bottom of chat with parallax effect
    function smoothScrollToBottom() {
        if (!chatLog) return;
        
        const scrollHeight = chatLog.scrollHeight;
        
        // Check if we're already at the bottom (within a small threshold)
        const isNearBottom = chatLog.scrollTop >= (scrollHeight - chatLog.clientHeight - 50);
        
        // Get all messages for potential parallax effect
        const messages = chatLog.querySelectorAll('.message');
        
        // Always do a smooth scroll for better UX
        try {
            // Use native smooth scrolling when possible
            chatLog.scrollTo({
                top: scrollHeight,
                behavior: isNearBottom ? 'auto' : 'smooth'
            });
            
            // Add subtle parallax effect on messages during scroll
            if (!isNearBottom && messages.length > 3) {
                // Only apply to visible messages when scrolling a larger distance
                const visibleMessages = Array.from(messages).slice(-5); // Last 5 messages
                
                // Create subtle movement effect
                visibleMessages.forEach((msg, idx) => {
                    const delay = idx * 60; // Staggered effect
                    setTimeout(() => {
                        msg.style.transform = 'translateY(-3px)';
                        setTimeout(() => {
                            msg.style.transform = '';
                        }, 300);
                    }, delay);
                });
            }
            
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

    // Toggle loading state with visual enhancements
    function setLoading(loading) {
        sendBtn.disabled = loading;
        progressIndicator.classList.toggle('d-none', !loading);
        
        // Update status indicator with enhanced visuals
        if (chatStatus) {
            if (loading) {
                chatStatus.className = 'badge rounded-pill bg-warning';
                chatStatus.innerHTML = '<span class="status-dot"></span> Procesando';
                
                // Add visual pulse effect to the card
                const card = document.querySelector('.card');
                if (card) {
                    card.style.transition = 'box-shadow 1s ease';
                    card.style.boxShadow = '0 0 20px rgba(138, 43, 226, 0.4)';
                }
                
                // Add visual effect to input field to show it's waiting
                if (questionEl) {
                    questionEl.style.opacity = '0.7';
                    questionEl.placeholder = 'Procesando tu consulta...';
                }
            } else {
                chatStatus.className = 'badge rounded-pill bg-success';
                chatStatus.innerHTML = '<span class="status-dot"></span> Activo';
                
                // Remove pulse effect
                const card = document.querySelector('.card');
                if (card) {
                    setTimeout(() => {
                        card.style.boxShadow = '';
                    }, 300);
                }
                
                // Restore input field
                if (questionEl) {
                    questionEl.style.opacity = '1';
                    questionEl.placeholder = '¿En qué puedo ayudarte?';
                    
                    // Highlight input field briefly to draw attention back to it
                    questionEl.classList.add('highlight-input');
                    setTimeout(() => {
                        questionEl.classList.remove('highlight-input');
                    }, 800);
                }
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

            console.log('Polling progress for key:', key);
            const url = new URL(window.location.origin + '/chatbot/api/progress/');
            url.searchParams.set('key', key);
            console.log('Polling URL:', url);
            const res = await fetch(url);
            console.log('Progress response status:', res.status);
            if (!res.ok) return;
            
            const data = await res.json();
            console.log('Progress data received:', data);
            if (data.status === 'ok') {
                const state = data.progress.state;
                markStep(state);
                
                // Actualizar el status-dot con estados específicos
                updateStatusDot(state);
                
                if (state && state !== 'done' && state !== 'error') {
                    console.log('Scheduling next poll for state:', state);
                    setTimeout(() => pollProgress(key), 1000); // Cambiado a 1 segundo
                } else {
                    // Asegurar que vuelva a estado activo cuando termine
                    console.log('Final state reached:', state);
                    setTimeout(() => {
                        if (chatStatus) {
                            chatStatus.className = 'badge rounded-pill bg-success';
                            chatStatus.innerHTML = '<span class="status-dot"></span> Activo';
                        }
                    }, 500);
                }
            }
        } catch (e) {
            console.error('poll error', e);
        }
    }

    // Nueva función para actualizar el status-dot según el estado
    function updateStatusDot(state) {
        if (!chatStatus) return;
        
        const statusMessages = {
            'queued': {
                className: 'badge rounded-pill bg-info',
                text: '<span class="status-dot status-dot-pulse"></span> En cola'
            },
            'gathering_context': {
                className: 'badge rounded-pill bg-primary',
                text: '<span class="status-dot status-dot-pulse"></span> Analizando contexto'
            },
            'calling_llm': {
                className: 'badge rounded-pill bg-warning',
                text: '<span class="status-dot status-dot-pulse"></span> Consultando IA'
            },
            'streaming_answer': {
                className: 'badge rounded-pill bg-warning',
                text: '<span class="status-dot status-dot-pulse"></span> Generando respuesta'
            },
            'done': {
                className: 'badge rounded-pill bg-success',
                text: '<span class="status-dot"></span> Completado'
            },
            'obteniendo_demanda': {
                className: 'badge rounded-pill bg-secondary',
                text: '<span class="status-dot status-dot-pulse"></span> Obteniendo demanda'
            },
            'ingresando_poder_judicial': {
                className: 'badge rounded-pill bg-secondary',
                text: '<span class="status-dot status-dot-pulse"></span> Ingresando al Poder Judicial'
            },
            'descargando_pdf_demanda': {
                className: 'badge rounded-pill bg-secondary',
                text: '<span class="status-dot status-dot-pulse"></span> Descargando PDF de demanda'
            },
            'descargando_tramites': {
                className: 'badge rounded-pill bg-secondary',
                text: '<span class="status-dot status-dot-pulse"></span> Descargando trámites'
            },
            'cargando_datos_en_llm': {
                className: 'badge rounded-pill bg-secondary',
                text: '<span class="status-dot status-dot-pulse"></span> Cargando datos en IA'
            },
            'error': {
                className: 'badge rounded-pill bg-danger',
                text: '<span class="status-dot status-dot-error"></span> Error'
            }
        };
        
        const status = statusMessages[state] || statusMessages['queued'];
        chatStatus.className = status.className;
        chatStatus.innerHTML = status.text;
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
    
    // Create floating glow points
    function createGlowPoints() {
        if (!cardBody) return;
        
        // Clear existing glow points
        document.querySelectorAll('.glow-point').forEach(el => el.remove());
        
        // Create new floating points with random positions and animation delays
        const numPoints = window.innerWidth < 768 ? 5 : 10;
        
        for (let i = 0; i < numPoints; i++) {
            const point = document.createElement('div');
            point.className = 'glow-point';
            
            // Random position within the chat area
            const xPos = 10 + Math.random() * (cardBody.offsetWidth - 20);
            const yPos = 10 + Math.random() * (cardBody.offsetHeight - 20);
            
            point.style.left = `${xPos}px`;
            point.style.top = `${yPos}px`;
            
            // Random animation delay and duration for more organic feel
            const delay = Math.random() * 5;
            const duration = 5 + Math.random() * 5;
            point.style.animationDelay = `${delay}s`;
            point.style.animationDuration = `${duration}s`;
            
            // Random size variation
            const size = 3 + Math.random() * 5;
            point.style.width = `${size}px`;
            point.style.height = `${size}px`;
            
            cardBody.appendChild(point);
        }
    }
    
    // Initialize - Add initial focus to textarea and setup helpers
    if (questionEl) {
        setTimeout(() => {
            questionEl.focus();
            initScrollToBottomButton();
            handleViewportChanges();
            createGlowPoints();
            
            // Re-create glow points on resize
            window.addEventListener('resize', () => {
                // Debounce the resize event
                clearTimeout(window.resizeTimer);
                window.resizeTimer = setTimeout(() => {
                    createGlowPoints();
                }, 250);
            });
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