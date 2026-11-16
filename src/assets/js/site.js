// Singer Kitchens: menu toggles, submenus, same-origin iframe auto-height, two-pin showroom map.
(function () {
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.menu-parent').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var li = btn.parentElement;
      var open = !li.classList.contains('open');
      document.querySelectorAll('.has-sub.open').forEach(function (o) {
        if (o !== li) { o.classList.remove('open'); o.querySelector('.menu-parent').setAttribute('aria-expanded', 'false'); }
      });
      li.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.has-sub')) {
      document.querySelectorAll('.has-sub.open').forEach(function (o) { o.classList.remove('open'); });
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') document.querySelectorAll('.has-sub.open').forEach(function (o) { o.classList.remove('open'); });
  });

  // YouTube: thumbnail until pressed, then the privacy-enhanced player (built by the Eleventy "speed" transform).
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a.yt');
    if (!a) return;
    e.preventDefault();
    var p = a.getAttribute('data-params') || '';
    var f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + a.getAttribute('data-yt') + p + (p.indexOf('?') > -1 ? '&' : '?') + 'autoplay=1';
    f.title = a.querySelector('.sr').textContent.replace(/^Play video: /, '');
    f.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    f.referrerPolicy = 'strict-origin-when-cross-origin';
    f.allowFullscreen = true;
    a.replaceWith(f);
  });

  // Embedded planning tool: grow the iframe to fit its content (same origin).
  document.querySelectorAll('iframe[data-autoheight]').forEach(function (f) {
    function fit() {
      try { var h = f.contentDocument.documentElement.scrollHeight; if (h) f.style.height = (h + 20) + 'px'; } catch (err) {}
    }
    f.addEventListener('load', function () { fit(); setInterval(fit, 1000); });
  });

  // Two-pin showroom map (Leaflet + OpenStreetMap), loaded only when the map is near the viewport.
  var mapEl = document.getElementById('twomap');
  if (mapEl) {
    var started = false;
    function start() {
      if (started) return; started = true;
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
      document.head.appendChild(css);
      var s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
      s.onload = function () {
        var pins = JSON.parse(mapEl.getAttribute('data-pins'));
        mapEl.innerHTML = '';
        var map = L.map(mapEl, { scrollWheelZoom: false });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
        var bounds = [];
        pins.forEach(function (p) {
          var m = L.marker([p.lat, p.lng], { title: p.name, alt: p.name }).addTo(map);
          m.bindPopup('<strong>' + p.name + '</strong><br>' + p.address + '<br><a href="' + p.directions + '" target="_blank" rel="noopener">Get Directions</a>');
          bounds.push([p.lat, p.lng]);
        });
        map.fitBounds(bounds, { padding: [40, 40] });
      };
      document.body.appendChild(s);
    }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es, o) { if (es[0].isIntersecting) { o.disconnect(); start(); } }, { rootMargin: '300px' }).observe(mapEl);
    } else { start(); }
  }

  // Image carousels: dots, swipe (CSS scroll snap), auto-advance every 4s; pauses on hover/focus.
  // With reduced motion set on the device, photos still change but switch instantly instead of sliding (site.css).
  document.querySelectorAll('.carousel').forEach(function (c) {
    var track = c.querySelector('.carousel-track');
    var slides = c.querySelectorAll('.carousel-slide');
    var dotsBox = c.querySelector('.carousel-dots');
    if (!track || slides.length < 2) return;
    var dots = [];
    slides.forEach(function (s, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-label', 'Show photo ' + (i + 1));
      b.addEventListener('click', function () { go(i); restart(); });
      dotsBox.appendChild(b);
      dots.push(b);
    });
    function current() { return Math.round(track.scrollLeft / track.clientWidth); }
    function mark() { var n = current(); dots.forEach(function (d, i) { d.setAttribute('aria-current', i === n ? 'true' : 'false'); }); }
    function go(i) { track.scrollTo({ left: i * track.clientWidth }); }
    track.addEventListener('scroll', function () { window.requestAnimationFrame(mark); }, { passive: true });
    mark();
    var timer = null, paused = false;
    function restart() {
      clearInterval(timer);
      timer = setInterval(function () { if (!paused && !document.hidden) go((current() + 1) % slides.length); }, 4000);
    }
    c.addEventListener('mouseenter', function () { paused = true; });
    c.addEventListener('mouseleave', function () { paused = false; });
    c.addEventListener('focusin', function () { paused = true; });
    c.addEventListener('focusout', function () { paused = false; });
    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); go(Math.min(current() + 1, slides.length - 1)); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); go(Math.max(current() - 1, 0)); }
    });
    restart();
  });

  // Photo galleries (portfolio projects, blog posts): a thumbnail opens the full photo in a lightbox with
  // previous / next, a counter, arrow keys, swipe, and Esc or a click outside the photo to close.
  // Each thumbnail is a plain link to the photo, so it still works if this script does not run.
  var box = null, list = [], at = 0, opener = null;
  function lightbox() {
    if (box) return box;
    box = document.createElement('dialog');
    box.className = 'lightbox';
    box.setAttribute('aria-label', 'Photo viewer');
    box.innerHTML =
      '<figure class="lb-stage"><img class="lb-img" alt=""><figcaption class="lb-count" aria-live="polite"></figcaption></figure>' +
      '<button type="button" class="lb-btn lb-prev" aria-label="Previous photo">&#8249;</button>' +
      '<button type="button" class="lb-btn lb-next" aria-label="Next photo">&#8250;</button>' +
      '<button type="button" class="lb-btn lb-close" aria-label="Close">&times;</button>';
    document.body.appendChild(box);
    box.querySelector('.lb-prev').addEventListener('click', function () { show(at - 1); });
    box.querySelector('.lb-next').addEventListener('click', function () { show(at + 1); });
    box.querySelector('.lb-close').addEventListener('click', function () { box.close(); });
    box.addEventListener('click', function (e) { if (e.target === box || e.target.classList.contains('lb-stage')) box.close(); });
    box.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); show(at + 1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(at - 1); }
    });
    var x0 = null;
    box.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(dx) > 40) show(at + (dx < 0 ? 1 : -1));
    });
    box.addEventListener('close', function () {
      document.documentElement.classList.remove('lb-open');
      if (opener) opener.focus();
    });
    return box;
  }
  function show(i) {
    at = (i + list.length) % list.length;
    var a = list[at], img = box.querySelector('.lb-img'), thumb = a.querySelector('img');
    img.src = a.getAttribute('href');
    img.alt = thumb ? thumb.alt : '';
    box.querySelector('.lb-count').textContent = (at + 1) + ' / ' + list.length;
    box.classList.toggle('lb-single', list.length < 2);
    // fetch the neighbours so the next tap is instant
    [at + 1, at - 1].forEach(function (j) { new Image().src = list[(j + list.length) % list.length].getAttribute('href'); });
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('.gallery a.gallery-item');
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button > 0) return;
    var d = lightbox();
    if (typeof d.showModal !== 'function') return; // very old browser: follow the link to the photo
    e.preventDefault();
    list = Array.prototype.slice.call(a.closest('.gallery').querySelectorAll('a.gallery-item'));
    opener = a;
    show(list.indexOf(a));
    document.documentElement.classList.add('lb-open');
    d.showModal();
  });
})();
