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
})();
