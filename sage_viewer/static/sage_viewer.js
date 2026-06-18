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

  // ─── Console auto-scroll (follow output) ──────────────────────────
  // The console history (in-panel + pop-out) appends entries via Vue.
  // Keep each `.sage-console-scroll` container pinned to the bottom so
  // new output stays visible — unless the user has scrolled up to read
  // back, in which case we leave their position alone.
  var NEAR_BOTTOM_PX = 48;
  function stickToBottom(el) {
    el.scrollTop = el.scrollHeight;
  }
  function isNearBottom(el) {
    return el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM_PX;
  }
  // One observer per container, attached lazily as they appear/change.
  var obs = new MutationObserver(function (mutations) {
    var seen = new Set();
    mutations.forEach(function (m) {
      var el = m.target;
      while (el && el !== document.body) {
        if (el.classList && el.classList.contains('sage-console-scroll')) break;
        el = el.parentElement;
      }
      if (!el || el === document.body || seen.has(el)) return;
      seen.add(el);
      // Only follow if the user was already at/near the bottom.
      if (el.__sageStick !== false) stickToBottom(el);
    });
  });
  obs.observe(document.body, { childList: true, subtree: true });

  // Track whether the user has scrolled away from the bottom so we can
  // pause auto-follow, and resume once they return to the bottom.
  document.addEventListener('scroll', function (e) {
    var el = e.target;
    if (!el || !el.classList || !el.classList.contains('sage-console-scroll'))
      return;
    el.__sageStick = isNearBottom(el);
  }, true);

  // ─── Keyboard fly navigation (WASD / arrow keys) ──────────────────
  // Holding a key flies the camera that way continuously. Each tick
  // clicks a hidden cam-<dir> button which the server turns into a
  // view-relative translation. Movement is gated out while typing in a
  // field so console / input keys aren't hijacked.
  var FLY_KEYS = {
    'w': 'forward', 'arrowup': 'forward',
    's': 'back',    'arrowdown': 'back',
    'a': 'left',    'arrowleft': 'left',
    'd': 'right',   'arrowright': 'right',
    'q': 'up',      'e': 'down'
  };
  var heldKeys = {};      // key -> true while physically held
  var dirCount = {};      // direction -> number of held keys mapping to it
  function inEditable(el) {
    if (!el) return false;
    var t = el.tagName;
    return t === 'INPUT' || t === 'TEXTAREA' || el.isContentEditable;
  }
  function clickBtn(id) {
    var b = document.getElementById(id);
    if (b) b.click();
  }
  function pressDir(dir) {
    dirCount[dir] = (dirCount[dir] || 0) + 1;
    if (dirCount[dir] === 1) clickBtn('cam-press-' + dir);   // 0 -> 1
  }
  function releaseDir(dir) {
    dirCount[dir] = (dirCount[dir] || 1) - 1;
    if (dirCount[dir] <= 0) { dirCount[dir] = 0; clickBtn('cam-release-' + dir); }
  }
  function releaseAll() {
    for (var d in dirCount) { if (dirCount[d] > 0) clickBtn('cam-release-' + d); }
    heldKeys = {}; dirCount = {};
  }
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (inEditable(e.target)) return;
    var k = (e.key || '').toLowerCase();
    var dir = FLY_KEYS[k];
    if (!dir) return;
    e.preventDefault();
    if (heldKeys[k]) return;        // ignore the OS auto-repeat
    heldKeys[k] = true;
    pressDir(dir);
  }, true);
  document.addEventListener('keyup', function (e) {
    var k = (e.key || '').toLowerCase();
    if (!heldKeys[k]) return;
    delete heldKeys[k];
    var dir = FLY_KEYS[k];
    if (dir) releaseDir(dir);
  }, true);
  window.addEventListener('blur', releaseAll);   // stop if focus leaves

  // Grab keyboard focus as soon as the page is up so WASD / arrow keys work
  // immediately, without the user having to click the viewport first.
  function grabKeyboardFocus() {
    if (!document.body) return;
    if (document.activeElement && inEditable(document.activeElement)) return;
    document.body.setAttribute('tabindex', '-1');
    try { window.focus(); document.body.focus(); } catch (e) {}
  }
  window.addEventListener('load', function () {
    grabKeyboardFocus();
    setTimeout(grabKeyboardFocus, 500);
    setTimeout(grabKeyboardFocus, 1500);
  });
})();
