// Mobile nav toggle
document.getElementById('navToggle')?.addEventListener('click', () => {
  document.getElementById('navLinks')?.classList.toggle('open');
});

// Auto-dismiss flash messages after 5 seconds
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => {
    if (el && el.parentElement) el.remove();
  }, 5000);
});
