// ==UserScript==
// @name         Grok Conversation → Embodied Saddle Bridge
// @namespace    https://github.com/embodi/reflexkernel
// @version      0.3 (enhanced debug + better message container detection)
// @description  Monitors the open Grok conversation for #tagged sensation/emotion states and forwards them to the local Conversation Sensation Bridge, which injects them into ReflexKernel via the saddle/interface.
// @author       Embodied Autonomic System
// @match        https://grok.x.ai/*
// @match        https://x.com/grok*
// @match        https://grok.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const BRIDGE_URL = 'http://127.0.0.1:9876/state';
    const SEEN_STATES = new Set();
    let observer = null;
    let lastCheck = 0;

    function extractStatesFromText(text) {
        if (!text) return [];
        // Match lines or tokens starting with # followed by word chars, allowing common separators
        const regex = /#([a-zA-Z0-9_-]+)/g;
        const matches = [];
        let match;
        while ((match = regex.exec(text)) !== null) {
            matches.push(match[1]);
        }
        return matches;
    }

    function sendStateToBridge(state, context) {
        const payload = {
            state: `#${state}`,
            context: context ? context.substring(0, 400) : '',
            source: 'grok_conversation'
        };

        GM_xmlhttpRequest({
            method: 'POST',
            url: BRIDGE_URL,
            data: JSON.stringify(payload),
            headers: {
                'Content-Type': 'application/json'
            },
            onload: function(response) {
                if (response.status >= 200 && response.status < 300) {
                    console.log(`[Grok→Saddle] Forwarded state: #${state}`);
                } else {
                    console.warn(`[Grok→Saddle] Bridge responded ${response.status}: ${response.responseText}`);
                }
            },
            onerror: function(err) {
                console.error('[Grok→Saddle] Failed to reach local bridge. Is scripts/conversation_sensation_bridge.py running?', err);
            }
        });
    }

    function scanConversation() {
        console.log('[Grok→Saddle] scanConversation() running...');

        // Try to find the main conversation container. Grok's UI changes frequently.
        // Prioritize elements that typically hold the actual chat messages.
        const containers = document.querySelectorAll(
            '[data-testid="conversation"], ' +
            '.conversation, ' +
            '.chat-messages, ' +
            'main, ' +
            '[class*="message"], ' +
            '[class*="ChatMessage"], ' +
            '[class*="prose"], ' +           // Grok often renders markdown in prose areas
            '[data-role="assistant"], ' +
            'div[role="article"], ' +
            '[class*="Message"]'
        );

        let fullText = '';
        containers.forEach(el => {
            fullText += ' ' + (el.innerText || el.textContent || '');
        });

        // Also scan the whole body as fallback (catches most rendered text)
        if (!fullText.trim() || fullText.length < 50) {
            fullText = document.body.innerText || document.body.textContent || '';
        }

        const states = extractStatesFromText(fullText);
        console.log(`[Grok→Saddle] Extracted ${states.length} state(s) from page:`, states);

        states.forEach(state => {
            if (!SEEN_STATES.has(state)) {
                SEEN_STATES.add(state);
                // Get surrounding context for richer seed
                const contextMatch = fullText.match(new RegExp(`.{0,180}#${state}.{0,180}`, 'i'));
                const context = contextMatch ? contextMatch[0] : fullText.substring(0, 400);
                console.log(`[Grok→Saddle] New unseen state detected: #${state} — sending to bridge`);
                sendStateToBridge(state, context);
            } else {
                // Uncomment the next line temporarily if you want to see deduping in action
                // console.log(`[Grok→Saddle] Ignoring already seen state: #${state}`);
            }
        });
    }

    function startMonitoring() {
        // MutationObserver for dynamic chat updates (new messages arriving)
        const targetNode = document.body;
        const config = { childList: true, subtree: true, characterData: true };

        observer = new MutationObserver((mutations) => {
            let shouldScan = false;
            for (const mutation of mutations) {
                if (mutation.addedNodes.length > 0 || mutation.type === 'characterData') {
                    shouldScan = true;
                    break;
                }
            }
            if (shouldScan) {
                // Debounce to avoid excessive scanning
                const now = Date.now();
                if (now - lastCheck > 800) {
                    lastCheck = now;
                    setTimeout(scanConversation, 150);
                }
            }
        });

        observer.observe(targetNode, config);

        // Periodic full scan as safety net (every 4 seconds)
        setInterval(scanConversation, 4000);

        // Initial scan
        setTimeout(scanConversation, 1500);

        console.log('%c[Grok→Saddle] Conversation monitor active. #states will be forwarded to the local bridge.', 'color:#4ade80');
        console.log('%c[Grok→Saddle] Make sure you have run: python scripts/conversation_sensation_bridge.py', 'color:#facc15');
        console.log('%c[Grok→Saddle] Debug: running on ' + window.location.href, 'color:#94a3b8');
        console.log('%c[Grok→Saddle] Tip: In console you can run: triggerGrokSaddleScan()  or  resetGrokSaddleSeen()', 'color:#64748b');
    }

    // Allow resetting seen states from console (useful during testing)
    window.resetGrokSaddleSeen = function() {
        SEEN_STATES.clear();
        console.log('[Grok→Saddle] SEEN_STATES cleared. Next #tags will be forwarded again.');
    };

    // Safety: only run on actual chat pages
    const isGrokPage = window.location.href.includes('grok') || 
                       window.location.href.includes('/chat') ||
                       window.location.hostname.includes('grok');

    if (isGrokPage) {
        console.log('[Grok→Saddle] Detected Grok page, starting monitor...');
        startMonitoring();
    } else {
        console.log('[Grok→Saddle] Not on a Grok chat page, monitor not started. Current URL:', window.location.href);
    }

    // Expose a manual trigger in console for testing
    window.triggerGrokSaddleScan = scanConversation;
})();