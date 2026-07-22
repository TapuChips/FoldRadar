/* FoldRadar — interactive foldable.
   Slider drives --fold (0 closed .. 1 open). Drag anywhere on the stage to spin
   the phone freely in 3D (full 360° horizontally); flick and let go to keep it
   spinning with momentum. Tap it (no drag) to fold/unfold. Auto-demos once. */
(function () {
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('[data-fold]').forEach(function (stage) {
    var range = stage.querySelector('.foldrange');
    var toggle = stage.querySelector('.foldtoggle');
    var view = stage.querySelector('.foldview');
    var phone = stage.querySelector('.foldphone');
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

    /* --- free 360° drag rotation with flick momentum --- */
    if (view && phone) {
      var rx = 6, ry = -16, vry = 0, dragging = false, moved = false, px = 0, py = 0, spinRaf = null;
      function applyRot() {
        phone.style.setProperty('--rotx', rx.toFixed(1) + 'deg');
        phone.style.setProperty('--roty', ry.toFixed(1) + 'deg');
      }
      function stopSpin() { if (spinRaf) { cancelAnimationFrame(spinRaf); spinRaf = null; } }
      function spin() {
        ry += vry;
        vry *= 0.94;                       // friction
        applyRot();
        spinRaf = Math.abs(vry) > 0.06 ? requestAnimationFrame(spin) : null;
      }
      view.addEventListener('pointerdown', function (e) {
        dragging = true; moved = false; px = e.clientX; py = e.clientY; vry = 0;
        stopSpin(); view.classList.add('grabbing');
        try { view.setPointerCapture(e.pointerId); } catch (err) {}
        handOff();
      });
      view.addEventListener('pointermove', function (e) {
        if (!dragging) return;
        var dx = e.clientX - px, dy = e.clientY - py;
        if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
        ry += dx * 0.5;                                    // no clamp → full 360°+
        rx = Math.max(-90, Math.min(90, rx - dy * 0.4));   // vertical tilt, capped
        vry = dx * 0.5;                                    // store velocity for momentum
        px = e.clientX; py = e.clientY;
        applyRot();
      });
      ['pointerup', 'pointercancel'].forEach(function (ev) {
        view.addEventListener(ev, function () {
          if (!dragging) return;
          dragging = false; view.classList.remove('grabbing');
          if (Math.abs(vry) > 0.5) spin();                 // flick to keep spinning
        });
      });
      view.addEventListener('click', function () {
        if (moved) { moved = false; return; }
        handOff(); apply(val < 50 ? 100 : 0);
      });
    }

    if (!reduce) {
      setTimeout(function () { if (!touched && !document.hidden) { dir = -1; raf = requestAnimationFrame(tick); } }, 1600);
      document.addEventListener('visibilitychange', function () { if (document.hidden) stopAuto(); });
    }
  });
})();
