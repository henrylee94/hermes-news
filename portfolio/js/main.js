/* =============================================================
   main.js — Theme toggle, hamburger menu, smooth scroll,
             language toggle stub (calls window.applyI18n)
   ============================================================= */

(function () {
  'use strict';

  // ── Theme toggle ────────────────────────────────────────────
  function getTheme() {
    return localStorage.getItem('theme') || 'dark';
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);

    // Update toggle button aria-label for accessibility
    var btn = document.querySelector('[data-action="toggle-theme"]');
    if (btn) {
      btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      btn.textContent = theme === 'dark' ? '☀' : '◑';
    }
  }

  function toggleTheme() {
    var current = getTheme();
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  // ── Language toggle ──────────────────────────────────────────
  function getLang() {
    return localStorage.getItem('lang') || 'en';
  }

  function applyLang(lang) {
    document.documentElement.lang = lang;
    localStorage.setItem('lang', lang);

    // Update toggle button label
    var btn = document.querySelector('[data-action="toggle-lang"]');
    if (btn) {
      btn.textContent = lang === 'en' ? '中' : 'EN';
      btn.setAttribute('aria-label', lang === 'en' ? 'Switch to Chinese' : 'Switch to English');
    }

    // Delegate to i18n module if loaded (Task 6)
    if (typeof window.applyI18n === 'function') {
      window.applyI18n();
    }
  }

  function toggleLang() {
    var current = getLang();
    applyLang(current === 'en' ? 'zh' : 'en');
  }

  // ── Hamburger (mobile nav) ───────────────────────────────────
  function initHamburger() {
    var topbar = document.querySelector('.topbar');
    var hamburger = document.querySelector('[data-action="toggle-menu"]');

    if (!topbar || !hamburger) return;

    hamburger.addEventListener('click', function () {
      topbar.classList.toggle('open');
      var isOpen = topbar.classList.contains('open');
      hamburger.setAttribute('aria-expanded', String(isOpen));
      hamburger.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
    });

    // Close mobile nav when clicking outside
    document.addEventListener('click', function (e) {
      if (!topbar.contains(e.target)) {
        topbar.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ── Smooth scroll for nav anchors ───────────────────────────
  function initSmoothScroll() {
    var topbar = document.querySelector('.topbar');

    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener('click', function (e) {
        var target = document.querySelector(link.getAttribute('href'));
        if (!target) return;

        e.preventDefault();

        // Close mobile menu if open
        if (topbar) topbar.classList.remove('open');

        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  // ── Boot ─────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // Wire theme toggle
    var themeBtn = document.querySelector('[data-action="toggle-theme"]');
    if (themeBtn) {
      themeBtn.addEventListener('click', toggleTheme);
      // Sync button label to current theme
      applyTheme(getTheme());
    }

    // Wire lang toggle
    var langBtn = document.querySelector('[data-action="toggle-lang"]');
    if (langBtn) {
      langBtn.addEventListener('click', toggleLang);
      // Sync button label to current lang
      applyLang(getLang());
    }

    initHamburger();
    initSmoothScroll();
  });
}());
