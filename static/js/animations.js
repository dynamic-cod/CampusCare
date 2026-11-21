/**
 * CampusCare Lightweight UI Animation & Micro-Interaction Engine
 * Linear/Vercel inspired, 60fps compositor-bound, zero-dependency.
 */
document.addEventListener('DOMContentLoaded', () => {
  initScrollReveals();
  initCursorSpotlight();
  initGridAccordions();
  initUpvoteSpringAnimations();
});

// 1. Staggered Blur-to-Sharp Intersection Observer
function initScrollReveals() {
  const elements = document.querySelectorAll('.reveal-up');
  if (!elements.length) return;

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, {
      rootMargin: '0px 0px -30px 0px',
      threshold: 0.05
    });

    elements.forEach(el => observer.observe(el));
  } else {
    // Fallback for older browsers
    elements.forEach(el => el.classList.add('is-revealed'));
  }
}

// 2. Cursor-Tracking Spotlight Glow
function initCursorSpotlight() {
  const cards = document.querySelectorAll('.spotlight-card');
  if (!cards.length) return;

  // Only bind mousemove if device supports hover (avoids useless touch listeners)
  if (window.matchMedia('(hover: hover)').matches) {
    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      });
    });
  }
}

// 3. Fluid Grid Accordions
function initGridAccordions() {
  const panel = document.getElementById('activePanel');
  if (panel && !panel.classList.contains('grid-accordion')) {
    panel.classList.add('grid-accordion');
  }

  // Define global toggleActivePanel function (single source of truth)
  window.toggleActivePanel = function() {
    const panel = document.getElementById('activePanel');
    const chevron = document.getElementById('chevron');
    const btn = document.getElementById('activeToggle');
    if (!panel || !btn) return;

    const isOpening = !panel.classList.contains('is-open');
    panel.classList.toggle('is-open', isOpening);
    btn.classList.toggle('is-open', isOpening);
    btn.setAttribute('aria-expanded', isOpening ? 'true' : 'false');
    if (chevron) {
      chevron.style.transform = isOpening ? 'rotate(180deg)' : 'rotate(0deg)';
    }
  };
}

// 4. Upvote Spring Animation Helper
function initUpvoteSpringAnimations() {
  document.addEventListener('click', (e) => {
    const upvoteBtn = e.target.closest('.upvote-btn');
    if (upvoteBtn) {
      upvoteBtn.classList.remove('upvote-pop');
      // trigger reflow
      void upvoteBtn.offsetWidth;
      upvoteBtn.classList.add('upvote-pop');
    }
  });
}

// Global copy-token feedback helper with animated toast state
window.copyTokenWithFeedback = function(token, btnId, textId) {
  if (!token) return;
  const btn = document.getElementById(btnId);
  const textEl = document.getElementById(textId);
  const originalHtml = textEl ? textEl.innerHTML : (btn ? btn.innerHTML : '');

  const showSuccess = () => {
    if (textEl) {
      textEl.innerHTML = '<span class="copied-toast">Copied ✓</span>';
    } else if (btn) {
      btn.innerHTML = '<span class="copied-toast">Copied ✓</span>';
    }
    setTimeout(() => {
      if (textEl) textEl.innerHTML = originalHtml;
      else if (btn) btn.innerHTML = originalHtml;
    }, 2200);
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(token).then(showSuccess).catch(() => {
      fallbackCopy(token, showSuccess);
    });
  } else {
    fallbackCopy(token, showSuccess);
  }
};

function fallbackCopy(text, cb) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    if (cb) cb();
  } catch (err) {
    console.error('Copy failed:', err);
  }
  document.body.removeChild(ta);
}
