/**
 * Restaurant Manager - Main Application JavaScript
 *
 * Table of Contents:
 *   1. Service Worker Registration
 *   2. API Helper
 *   3. Toast Notification System
 *   4. Formatting Utilities
 *   5. Theme Toggle (Dark / Light Mode)
 *   6. Debounce Utility
 *   7. Auto-Refresh Mechanism
 *   8. Modal Helpers
 *   9. PWA Install Prompt
 *  10. Online / Offline Status Indicator
 *  11. Navigation Highlight
 *  12. Touch Gesture Helpers (Swipe Detection)
 *  13. Initialization
 */

(function () {
  'use strict';

  /* ========================================================================
     1. Service Worker Registration
     ======================================================================== */

  /**
   * Register the service worker located at /static/sw.js.
   * Called once during page initialisation.
   */
  function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) {
      return;
    }

    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/static/sw.js', { scope: '/' })
        .then((registration) => {
          console.log('[App] Service Worker registered, scope:', registration.scope);

          // Listen for updates.
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (!newWorker) return;

            newWorker.addEventListener('statechange', () => {
              if (
                newWorker.state === 'activated' &&
                navigator.serviceWorker.controller
              ) {
                showToast('App updated. Refresh for the latest version.', 'info');
              }
            });
          });
        })
        .catch((error) => {
          console.error('[App] Service Worker registration failed:', error);
        });
    });
  }

  /* ========================================================================
     2. API Helper
     ======================================================================== */

  /**
   * Perform an API call with automatic JSON handling.
   *
   * @param {string}      url            - The endpoint URL (e.g. "/api/orders").
   * @param {string}      [method=GET]   - HTTP method.
   * @param {Object|null} [body=null]    - Request payload (will be stringified).
   * @returns {Promise<Object>}          - Parsed JSON response.
   */
  async function api(url, method = 'GET', body = null) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    };

    if (body !== null && body !== undefined) {
      options.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(url, options);
    } catch (networkError) {
      showToast('Network error. Please check your connection.', 'error');
      throw networkError;
    }

    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      if (!response.ok) {
        showToast('Something went wrong.', 'error');
        throw new Error(`HTTP ${response.status}: Non-JSON response`);
      }
      return {};
    }

    if (!response.ok) {
      const message = data.error || data.message || 'Something went wrong.';
      showToast(message, 'error');
      throw new Error(message);
    }

    return data;
  }

  /* ========================================================================
     3. Toast Notification System
     ======================================================================== */

  /** Ensure the toast container exists in the DOM. */
  function getToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.setAttribute('aria-live', 'polite');
      container.setAttribute('aria-atomic', 'true');

      // Inline styles so the toast system works without extra CSS dependencies.
      Object.assign(container.style, {
        position: 'fixed',
        top: '1.25rem',
        right: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        zIndex: '9999',
        pointerEvents: 'none',
        maxWidth: '380px',
        width: '100%',
      });

      document.body.appendChild(container);
    }
    return container;
  }

  /** Colour map for toast types. */
  const TOAST_COLOURS = {
    success: { bg: '#27ae60', text: '#ffffff' },
    error:   { bg: '#e74c3c', text: '#ffffff' },
    warning: { bg: '#f39c12', text: '#ffffff' },
    info:    { bg: '#3498db', text: '#ffffff' },
  };

  /** Icon prefix characters for each toast type. */
  const TOAST_ICONS = {
    success: '\u2714',  // check mark
    error:   '\u2716',  // cross mark
    warning: '\u26A0',  // warning sign
    info:    '\u2139',  // info circle
  };

  /**
   * Display a toast notification.
   *
   * @param {string} message           - The message to display.
   * @param {string} [type=info]       - One of "success", "error", "warning", "info".
   * @param {number} [duration=4000]   - Time in ms before auto-dismiss.
   */
  function showToast(message, type = 'info', duration = 4000) {
    const container = getToastContainer();
    const colours = TOAST_COLOURS[type] || TOAST_COLOURS.info;
    const icon = TOAST_ICONS[type] || TOAST_ICONS.info;

    const toast = document.createElement('div');
    toast.setAttribute('role', 'status');
    Object.assign(toast.style, {
      background: colours.bg,
      color: colours.text,
      padding: '0.75rem 1.25rem',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      fontSize: '0.9rem',
      lineHeight: '1.4',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      pointerEvents: 'auto',
      opacity: '0',
      transform: 'translateX(30px)',
      transition: 'opacity 0.3s ease, transform 0.3s ease',
      cursor: 'pointer',
      wordBreak: 'break-word',
    });

    toast.innerHTML =
      '<span style="font-size:1.1rem;flex-shrink:0;">' + icon + '</span>' +
      '<span>' + escapeHtml(message) + '</span>';

    // Click to dismiss early.
    toast.addEventListener('click', () => dismissToast(toast));

    container.appendChild(toast);

    // Trigger entrance animation.
    requestAnimationFrame(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateX(0)';
    });

    // Auto-dismiss.
    if (duration > 0) {
      setTimeout(() => dismissToast(toast), duration);
    }
  }

  /** Remove a toast element with an exit animation. */
  function dismissToast(toast) {
    if (!toast || !toast.parentNode) return;
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }

  /** Simple HTML-escape to prevent XSS in toast messages. */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /* ========================================================================
     4. Formatting Utilities
     ======================================================================== */

  /**
   * Format a numeric amount as USD currency.
   *
   * @param {number} amount - Dollar amount.
   * @returns {string}      - e.g. "$12.50"
   */
  function formatCurrency(amount) {
    const num = Number(amount);
    if (Number.isNaN(num)) return '$0.00';

    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(num);
  }

  /**
   * Return a human-friendly relative time string.
   *
   * @param {string} isoString - An ISO 8601 date-time string.
   * @returns {string}         - e.g. "5 min ago", "2 hr ago", "just now"
   */
  function formatTime(isoString) {
    if (!isoString) return '';

    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';

    const now = Date.now();
    const diffSeconds = Math.floor((now - date.getTime()) / 1000);

    if (diffSeconds < 0)          return 'just now';
    if (diffSeconds < 10)         return 'just now';
    if (diffSeconds < 60)         return diffSeconds + ' sec ago';
    if (diffSeconds < 3600) {
      const minutes = Math.floor(diffSeconds / 60);
      return minutes + ' min ago';
    }
    if (diffSeconds < 86400) {
      const hours = Math.floor(diffSeconds / 3600);
      return hours + ' hr ago';
    }
    if (diffSeconds < 604800) {
      const days = Math.floor(diffSeconds / 86400);
      return days + (days === 1 ? ' day ago' : ' days ago');
    }

    // Older than a week — show a short date.
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  }

  /**
   * Format an ISO date-time string into a full, human-readable display.
   *
   * @param {string} isoString - An ISO 8601 date-time string.
   * @returns {string}         - e.g. "Feb 14, 2026 at 3:05 PM"
   */
  function formatDateTime(isoString) {
    if (!isoString) return '';

    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';

    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }) + ' at ' + date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  }

  /* ========================================================================
     5. Theme Toggle (Dark / Light Mode)
     ======================================================================== */

  const THEME_KEY = 'restaurant-manager-theme';

  /**
   * Apply the given theme to the document and persist it.
   *
   * @param {'dark'|'light'} theme
   */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);

    // Update the toggle button label if present.
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.textContent = theme === 'dark' ? '\u2600' : '\u263E'; // sun / moon
      btn.setAttribute(
        'aria-label',
        theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
      );
    }
  }

  /** Toggle between dark and light themes. */
  function toggleTheme() {
    const current = localStorage.getItem(THEME_KEY) || 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  /** Inject the theme toggle button into the navbar (if not already present). */
  function injectThemeToggle() {
    if (document.getElementById('theme-toggle')) return;

    const navbar = document.querySelector('.navbar');
    if (!navbar) return;

    const btn = document.createElement('button');
    btn.id = 'theme-toggle';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Toggle theme');
    Object.assign(btn.style, {
      background: 'transparent',
      border: '1px solid rgba(255,255,255,0.25)',
      color: '#fff',
      fontSize: '1.2rem',
      padding: '0.3rem 0.6rem',
      borderRadius: '6px',
      cursor: 'pointer',
      marginLeft: 'auto',
      lineHeight: '1',
      transition: 'background 0.2s',
    });

    btn.addEventListener('click', toggleTheme);
    btn.addEventListener('mouseenter', () => {
      btn.style.background = 'rgba(255,255,255,0.15)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.background = 'transparent';
    });

    navbar.appendChild(btn);
  }

  /** Initialise theme from stored preference or OS preference. */
  function initTheme() {
    injectThemeToggle();

    const stored = localStorage.getItem(THEME_KEY);
    if (stored) {
      applyTheme(stored);
      return;
    }

    // Respect OS-level preference.
    if (
      window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
    ) {
      applyTheme('dark');
    } else {
      applyTheme('light');
    }
  }

  /* ========================================================================
     6. Debounce Utility
     ======================================================================== */

  /**
   * Create a debounced version of a function.
   *
   * @param {Function} fn       - The function to debounce.
   * @param {number}   delay    - Delay in milliseconds (default 300).
   * @returns {Function}        - The debounced wrapper.
   */
  function debounce(fn, delay = 300) {
    let timerId = null;

    function debounced(...args) {
      if (timerId !== null) {
        clearTimeout(timerId);
      }
      timerId = setTimeout(() => {
        timerId = null;
        fn.apply(this, args);
      }, delay);
    }

    /** Cancel any pending invocation. */
    debounced.cancel = function () {
      if (timerId !== null) {
        clearTimeout(timerId);
        timerId = null;
      }
    };

    return debounced;
  }

  /* ========================================================================
     7. Auto-Refresh Mechanism
     ======================================================================== */

  /** @type {number|null} Active interval ID. */
  let autoRefreshInterval = null;

  /** @type {Function|null} The callback invoked on each tick. */
  let autoRefreshCallback = null;

  /**
   * Start auto-refreshing by calling `callback` every `intervalMs` milliseconds.
   * Only one auto-refresh can be active at a time; calling this again replaces
   * the previous one.
   *
   * @param {Function} callback      - Function to call on each tick.
   * @param {number}   [intervalMs]  - Interval in ms (default 30000 = 30 s).
   */
  function startAutoRefresh(callback, intervalMs = 30000) {
    stopAutoRefresh();
    autoRefreshCallback = callback;
    autoRefreshInterval = setInterval(() => {
      // Only refresh when the tab is visible and online.
      if (!document.hidden && navigator.onLine) {
        callback();
      }
    }, intervalMs);
  }

  /** Stop the current auto-refresh, if active. */
  function stopAutoRefresh() {
    if (autoRefreshInterval !== null) {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = null;
      autoRefreshCallback = null;
    }
  }

  /**
   * Check whether auto-refresh is currently active.
   *
   * @returns {boolean}
   */
  function isAutoRefreshActive() {
    return autoRefreshInterval !== null;
  }

  /**
   * Toggle auto-refresh on or off. When toggling on, requires the callback
   * that was previously set or a new one passed in.
   *
   * @param {Function} [callback]      - Refresh callback (optional if resuming).
   * @param {number}   [intervalMs]    - Interval in ms.
   * @returns {boolean}                - Whether auto-refresh is now active.
   */
  function toggleAutoRefresh(callback, intervalMs = 30000) {
    if (isAutoRefreshActive()) {
      stopAutoRefresh();
      return false;
    }

    const cb = callback || autoRefreshCallback;
    if (cb) {
      startAutoRefresh(cb, intervalMs);
      return true;
    }

    return false;
  }

  // Pause auto-refresh when the tab is hidden; resume when visible.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && autoRefreshInterval !== null) {
      // We don't clear the interval — the guard inside the setInterval
      // callback already skips execution when hidden. This avoids losing
      // the timer reference.
    }
  });

  /* ========================================================================
     8. Modal Helpers
     ======================================================================== */

  /**
   * Open a modal overlay by its element ID.
   *
   * @param {string} id - The ID of the `.modal-overlay` element.
   */
  function openModal(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Focus the first interactive element inside the modal for accessibility.
    requestAnimationFrame(() => {
      const focusable = overlay.querySelector(
        'input, select, textarea, button, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable) focusable.focus();
    });
  }

  /**
   * Close a modal overlay by its element ID.
   *
   * @param {string} id - The ID of the `.modal-overlay` element.
   */
  function closeModal(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  /**
   * Set up global modal behaviours:
   *   - Clicking on the overlay (outside the modal) closes it.
   *   - Pressing Escape closes the topmost open modal.
   */
  function initModalListeners() {
    // Close when clicking on overlay background.
    document.addEventListener('click', (e) => {
      if (
        e.target.classList.contains('modal-overlay') &&
        e.target.classList.contains('active')
      ) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
      }
    });

    // Close topmost modal on Escape.
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal-overlay.active');
        if (openModals.length > 0) {
          const topmost = openModals[openModals.length - 1];
          topmost.classList.remove('active');
          document.body.style.overflow = '';
        }
      }
    });
  }

  /* ========================================================================
     9. PWA Install Prompt
     ======================================================================== */

  /** @type {BeforeInstallPromptEvent|null} */
  let deferredInstallPrompt = null;

  /** Listen for the browser's install prompt event. */
  function initInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
      // Prevent the default mini-infobar.
      e.preventDefault();
      deferredInstallPrompt = e;

      // Show a custom install button if one exists in the DOM.
      const installBtn = document.getElementById('pwa-install-btn');
      if (installBtn) {
        installBtn.style.display = 'inline-flex';
        installBtn.addEventListener('click', promptInstall, { once: true });
      }
    });

    // Detect when the app is successfully installed.
    window.addEventListener('appinstalled', () => {
      deferredInstallPrompt = null;
      showToast('App installed successfully!', 'success');

      const installBtn = document.getElementById('pwa-install-btn');
      if (installBtn) {
        installBtn.style.display = 'none';
      }
    });
  }

  /**
   * Programmatically trigger the PWA install prompt.
   * Resolves to true if the user accepted, false otherwise.
   *
   * @returns {Promise<boolean>}
   */
  async function promptInstall() {
    if (!deferredInstallPrompt) {
      showToast(
        'Install is not available. You may already have the app installed.',
        'info'
      );
      return false;
    }

    deferredInstallPrompt.prompt();
    const { outcome } = await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;

    if (outcome === 'accepted') {
      showToast('Installing app...', 'success');
      return true;
    }

    return false;
  }

  /* ========================================================================
     10. Online / Offline Status Indicator
     ======================================================================== */

  /** Create and manage the online/offline status banner. */
  function initConnectivityIndicator() {
    // Create an indicator element that slides in when offline.
    const indicator = document.createElement('div');
    indicator.id = 'connectivity-indicator';
    indicator.setAttribute('role', 'alert');
    Object.assign(indicator.style, {
      position: 'fixed',
      bottom: '0',
      left: '0',
      width: '100%',
      padding: '0.5rem 1rem',
      textAlign: 'center',
      fontSize: '0.85rem',
      fontWeight: '600',
      zIndex: '10000',
      transform: 'translateY(100%)',
      transition: 'transform 0.3s ease, background 0.3s ease',
      pointerEvents: 'none',
    });

    document.body.appendChild(indicator);

    function showOffline() {
      indicator.textContent = 'You are offline. Some features may be unavailable.';
      indicator.style.background = '#e74c3c';
      indicator.style.color = '#ffffff';
      indicator.style.transform = 'translateY(0)';
    }

    function showOnline() {
      indicator.textContent = 'Back online.';
      indicator.style.background = '#27ae60';
      indicator.style.color = '#ffffff';
      indicator.style.transform = 'translateY(0)';

      setTimeout(() => {
        indicator.style.transform = 'translateY(100%)';
      }, 3000);
    }

    window.addEventListener('offline', showOffline);
    window.addEventListener('online', showOnline);

    // Show immediately if already offline on load.
    if (!navigator.onLine) {
      showOffline();
    }
  }

  /* ========================================================================
     11. Navigation Highlight
     ======================================================================== */

  /**
   * Highlight the navigation link that matches the current page path.
   * Replaces the inline script that was previously in base.html.
   */
  function highlightActiveNav() {
    const currentPath = window.location.pathname;

    document.querySelectorAll('.nav-links a').forEach((link) => {
      link.classList.remove('active');
      const href = link.getAttribute('href');

      if (href === currentPath) {
        link.classList.add('active');
      } else if (href !== '/' && currentPath.startsWith(href)) {
        // Handle sub-paths (e.g. /orders/123 highlights /orders).
        link.classList.add('active');
      }
    });
  }

  /* ========================================================================
     12. Touch Gesture Helpers (Swipe Detection)
     ======================================================================== */

  /**
   * Attach swipe detection to an element.
   *
   * @param {HTMLElement}  element    - The DOM element to listen on.
   * @param {Object}       callbacks  - Map of direction to handler:
   *   { left: fn, right: fn, up: fn, down: fn }
   * @param {Object}       [options]
   * @param {number}       [options.threshold=50]    - Min distance in px.
   * @param {number}       [options.restraint=100]   - Max perpendicular distance.
   * @param {number}       [options.maxTime=500]     - Max duration in ms.
   * @returns {Function}   A cleanup function that removes the listeners.
   */
  function onSwipe(element, callbacks, options = {}) {
    const threshold = options.threshold || 50;
    const restraint = options.restraint || 100;
    const maxTime = options.maxTime || 500;

    let startX = 0;
    let startY = 0;
    let startTime = 0;

    function handleTouchStart(e) {
      const touch = e.changedTouches[0];
      startX = touch.pageX;
      startY = touch.pageY;
      startTime = Date.now();
    }

    function handleTouchEnd(e) {
      const touch = e.changedTouches[0];
      const dx = touch.pageX - startX;
      const dy = touch.pageY - startY;
      const elapsed = Date.now() - startTime;

      if (elapsed > maxTime) return;

      const absDx = Math.abs(dx);
      const absDy = Math.abs(dy);

      // Horizontal swipe.
      if (absDx >= threshold && absDy <= restraint) {
        if (dx > 0 && callbacks.right) {
          callbacks.right(e);
        } else if (dx < 0 && callbacks.left) {
          callbacks.left(e);
        }
      }

      // Vertical swipe.
      if (absDy >= threshold && absDx <= restraint) {
        if (dy > 0 && callbacks.down) {
          callbacks.down(e);
        } else if (dy < 0 && callbacks.up) {
          callbacks.up(e);
        }
      }
    }

    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });

    // Return a cleanup function.
    return function removeSwipeListeners() {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  }

  /* ========================================================================
     13. Initialization
     ======================================================================== */

  /**
   * Bootstrap all application-level features.
   * Called once when the DOM is ready.
   */
  function init() {
    registerServiceWorker();
    initTheme();
    initModalListeners();
    initInstallPrompt();
    initConnectivityIndicator();
    highlightActiveNav();
  }

  // Run init when the DOM is ready.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* ========================================================================
     Public API — expose utilities on the global `App` namespace so that
     page-specific scripts and inline handlers can use them.
     ======================================================================== */

  window.App = {
    // API
    api,

    // Toasts
    showToast,

    // Formatting
    formatCurrency,
    formatTime,
    formatDateTime,

    // Theme
    toggleTheme,

    // Debounce
    debounce,

    // Auto-refresh
    startAutoRefresh,
    stopAutoRefresh,
    isAutoRefreshActive,
    toggleAutoRefresh,

    // Modals
    openModal,
    closeModal,

    // PWA install
    promptInstall,

    // Touch
    onSwipe,

    // Navigation
    highlightActiveNav,
  };

  // Also expose the api function at the top level for backward compatibility
  // with existing inline scripts that call `api(url, method, body)` directly.
  window.api = api;
  window.showToast = showToast;
  window.formatCurrency = formatCurrency;
  window.formatTime = formatTime;
  window.formatDateTime = formatDateTime;
  window.openModal = openModal;
  window.closeModal = closeModal;
  window.debounce = debounce;
})();
