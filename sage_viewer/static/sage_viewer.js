// SAGE-Viewer client-side helpers — served via trame's module system.
// Vue 3 silently strips <script> tags from templates, so any client JS
// has to come in via a real .js file the browser can load.
(function () {
  // ─── Pop-out console drag handler ─────────────────────────────────
  // Mousedown on `.sage-popout-handle` starts a drag of the nearest
  // `.sage-popout` ancestor. Repositions via left/top, clearing the
  // initial right/bottom anchors so the move actually applies.
  document.addEventListener('mousedown', function (e) {
    var handle = e.target.closest && e.target.closest('.sage-popout-handle');
    if (!handle) return;
    var card = handle.closest('.sage-popout');
    if (!card) return;
    e.preventDefault();
    var startX = e.clientX, startY = e.clientY;
    var startLeft = card.offsetLeft, startTop = card.offsetTop;
    card.style.right  = 'auto';
    card.style.bottom = 'auto';
    card.style.left   = startLeft + 'px';
    card.style.top    = startTop  + 'px';
    function mv(ev) {
      card.style.left = (startLeft + ev.clientX - startX) + 'px';
      card.style.top  = (startTop  + ev.clientY - startY) + 'px';
    }
    function up() {
      document.removeEventListener('mousemove', mv);
      document.removeEventListener('mouseup',   up);
    }
    document.addEventListener('mousemove', mv);
    document.addEventListener('mouseup',   up);
  });

  // ─── Enter-to-click ───────────────────────────────────────────────
  // Any <input> / <textarea> whose ancestor declares
  // `data-enter-click="<button-id>"` will, on Enter, trigger a click
  // on the element with that id. Reliable because it bypasses
  // Vuetify's internal event handling entirely — we just simulate
  // the user clicking the action button.
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    if (e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) return;
    var inp = e.target;
    if (!inp) return;
    var tag = inp.tagName;
    if (tag !== 'INPUT' && tag !== 'TEXTAREA') return;
    var el = inp;
    while (el && el !== document.body) {
      var act = el.getAttribute && el.getAttribute('data-enter-click');
      if (act) {
        var btn = document.getElementById(act);
        if (btn) {
          e.preventDefault();
          btn.click();
        }
        return;
      }
      el = el.parentElement;
    }
  }, true);  // capture phase so we beat Vuetify's listeners
})();
