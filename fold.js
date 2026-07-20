/* FoldRadar — interactive foldable. Slider + tap drive --fold (0 closed .. 1 open).
   Auto-demos once, then hands control to the user on first interaction. */
(function () {
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('[data-fold]').forEach(function (stage) {
    var range = stage.querySelector('.foldrange');
    var toggle = stage.querySelector('.foldtoggle');
    var val = 100, dir = -1, raf = null, touched = false, dragTimer = null;

    function apply(v) {
      val = Math.max(0, Math.min(100, v));
      stage.style.setProperty('--fold', (val / 100).toFixed(3));
      if (range && Math.round(+range.value) !== Math.round(val)) range.value = val;
    }
    apply(100);

    function stopAuto() { if (raf) { cancelAnimationFrame(raf); raf = null; } }
    function tick() {
      val += dir * 0.55;
      if (val <= 6) { val = 6; dir = 1; }
      else if (val >= 100) { val = 100; dir = -1; }
      apply(val);
      raf = requestAnimationFrame(tick);
    }
    function handOff() { if (!touched) { touched = true; stopAuto(); } }

    if (range) {
      range.addEventListener('input', function () {
        handOff();
        stage.classList.add('dragging');
        clearTimeout(dragTimer);
        dragTimer = setTimeout(function () { stage.classList.remove('dragging'); }, 140);
        apply(+range.value);
      });
    }
    if (toggle) {
      toggle.addEventListener('click', function () { handOff(); apply(val < 50 ? 100 : 0); });
    }

    if (!reduce) {
      setTimeout(function () { if (!touched && !document.hidden) { dir = -1; raf = requestAnimationFrame(tick); } }, 1600);
      document.addEventListener('visibilitychange', function () { if (document.hidden) stopAuto(); });
    }
  });
})();
