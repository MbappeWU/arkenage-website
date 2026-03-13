/* ==================================================================
   MacSweep Landing Page — English Version Scripts
   ================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initScrollAnimations();
  initNavbar();
  initSmoothScroll();
  initHamburgerMenu();
});

/* --- Scroll Animations (IntersectionObserver) --- */
function initScrollAnimations() {
  const elements = document.querySelectorAll('.fade-up');
  if (!elements.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );

  elements.forEach((el) => observer.observe(el));
}

/* --- Navbar: transparent → glassmorphism on scroll --- */
function initNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const onScroll = () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

/* --- Smooth Scrolling for Anchor Links --- */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const targetId = anchor.getAttribute('href');
      if (targetId === '#') return;

      const target = document.querySelector(targetId);
      if (!target) return;

      e.preventDefault();
      const navHeight = document.getElementById('navbar')?.offsetHeight || 0;
      const targetPos = target.getBoundingClientRect().top + window.scrollY - navHeight;

      window.scrollTo({ top: targetPos, behavior: 'smooth' });

      // Close mobile menu if open
      const navLinks = document.getElementById('nav-links');
      const hamburger = document.getElementById('hamburger');
      if (navLinks?.classList.contains('open')) {
        navLinks.classList.remove('open');
        hamburger?.classList.remove('active');
      }
    });
  });
}

/* --- Mobile Hamburger Menu --- */
function initHamburgerMenu() {
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');
  if (!hamburger || !navLinks) return;

  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    hamburger.classList.toggle('active');
  });
}
