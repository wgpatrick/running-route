(function () {
  // one tooltip for every mark that carries data-tip; the same text shows on keyboard focus
  var tip = document.getElementById('tip');
  function show(el, x, y) {
    var t = el.getAttribute('data-tip');
    if (!t) { tip.hidden = true; return; }
    tip.textContent = t;
    tip.hidden = false;
    var r = tip.getBoundingClientRect(), vw = document.documentElement.clientWidth, vh = window.innerHeight;
    var left = Math.min(Math.max(8, x + 12), vw - r.width - 8);
    var top = y + 16 + r.height > vh ? y - r.height - 10 : y + 16;
    tip.style.left = left + 'px';
    tip.style.top = Math.max(8, top) + 'px';
  }
  document.addEventListener('pointermove', function (ev) {
    var el = ev.target.closest ? ev.target.closest('[data-tip]') : null;
    if (el) show(el, ev.clientX, ev.clientY); else tip.hidden = true;
  });
  document.addEventListener('pointerleave', function () { tip.hidden = true; });
  document.addEventListener('focusin', function (ev) {
    var el = ev.target.closest ? ev.target.closest('[data-tip]') : null;
    if (el) { var r = el.getBoundingClientRect(); show(el, r.left + Math.min(r.width / 2, 160), r.bottom - 8); }
  });
  document.addEventListener('focusout', function () { tip.hidden = true; });
  window.addEventListener('scroll', function () { tip.hidden = true; }, { passive: true });

  // a pin and its line in the list light up together
  function hot(k, on) {
    document.querySelectorAll('[data-k="' + k + '"]').forEach(function (n) { n.classList.toggle('hot', on); });
  }
  document.querySelectorAll('[data-k]').forEach(function (n) {
    var k = n.getAttribute('data-k');
    n.addEventListener('pointerenter', function () { hot(k, true); });
    n.addEventListener('pointerleave', function () { hot(k, false); });
  });
})();
