/* Swipe left/right on touch screens to move between the main pages, in rail order
   (Home, About, Experience, Projects, Contact). Swipe left = next page, swipe right = previous.
   The order is read from the rail dots, so it follows the nav without a second list to maintain.
   Pages with no ringed dot (testimonials, posts) are left alone. No wrap at either end. */
(function(){
  var rail = document.querySelectorAll('.rail a');
  var current = -1;
  for (var i = 0; i < rail.length; i++) { if (rail[i].classList.contains('on')) current = i; }
  if (current < 0) return;

  var MIN_X = 70, MAX_MS = 700, RATIO = 1.6;
  var start = null;

  function blocked(el){
    var menu = document.getElementById('menu');
    if (menu && !menu.hidden) return true;
    for (; el && el !== document.body; el = el.parentElement) {
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable) return true;
      if (el.scrollWidth > el.clientWidth + 1 && /(auto|scroll)/.test(getComputedStyle(el).overflowX)) return true;
    }
    return false;
  }

  document.addEventListener('touchstart', function(e){
    var zoomed = window.visualViewport && window.visualViewport.scale > 1.01;
    if (e.touches.length !== 1 || zoomed || blocked(e.target)) { start = null; return; }
    start = { x: e.touches[0].clientX, y: e.touches[0].clientY, t: Date.now() };
  }, { passive: true });

  document.addEventListener('touchcancel', function(){ start = null; }, { passive: true });

  document.addEventListener('touchend', function(e){
    if (!start) return;
    var t = e.changedTouches[0], dx = t.clientX - start.x, dy = t.clientY - start.y, ms = Date.now() - start.t;
    start = null;
    if (ms > MAX_MS || Math.abs(dx) < MIN_X || Math.abs(dx) < Math.abs(dy) * RATIO) return;
    var sel = window.getSelection && window.getSelection();
    if (sel && String(sel).length) return;
    var next = rail[current + (dx < 0 ? 1 : -1)];
    if (next) window.location.href = next.getAttribute('href');
  }, { passive: true });
})();
