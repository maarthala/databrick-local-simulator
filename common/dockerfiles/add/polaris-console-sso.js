// Plain-http hosts (k8s: http://polaris-console.de.lan) are not a "secure context", so the
// browser hides crypto.subtle — and the console's PKCE sign-in calls crypto.subtle.digest
// ("Cannot read properties of undefined (reading 'digest')"). localhost is secure, so local
// never needed this. Provide SHA-256 (the only digest it uses) when the browser doesn't.
(function () {
  var c = window.crypto;
  if (!c || (c.subtle && c.subtle.digest)) return;
  var K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  function sha256(bytes) {
    var n = bytes.length, len = ((n + 9 + 63) >> 6) << 6, m = new Uint8Array(len), dv = new DataView(m.buffer);
    m.set(bytes); m[n] = 0x80; dv.setUint32(len - 4, n * 8); dv.setUint32(len - 8, Math.floor(n / 0x20000000));
    var h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19], w = new Array(64);
    function r(x, k) { return (x >>> k) | (x << (32 - k)); }
    for (var o = 0; o < len; o += 64) {
      for (var i = 0; i < 16; i++) w[i] = dv.getUint32(o + i * 4);
      for (i = 16; i < 64; i++) {
        var s0 = r(w[i-15], 7) ^ r(w[i-15], 18) ^ (w[i-15] >>> 3), s1 = r(w[i-2], 17) ^ r(w[i-2], 19) ^ (w[i-2] >>> 10);
        w[i] = (w[i-16] + s0 + w[i-7] + s1) | 0;
      }
      var a = h[0], b = h[1], cc = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
      for (i = 0; i < 64; i++) {
        var t1 = (hh + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) | 0;
        var t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & cc) ^ (b & cc))) | 0;
        hh = g; g = f; f = e; e = (d + t1) | 0; d = cc; cc = b; b = a; a = (t1 + t2) | 0;
      }
      h[0] = (h[0] + a) | 0; h[1] = (h[1] + b) | 0; h[2] = (h[2] + cc) | 0; h[3] = (h[3] + d) | 0;
      h[4] = (h[4] + e) | 0; h[5] = (h[5] + f) | 0; h[6] = (h[6] + g) | 0; h[7] = (h[7] + hh) | 0;
    }
    var out = new Uint8Array(32), odv = new DataView(out.buffer);
    for (i = 0; i < 8; i++) odv.setUint32(i * 4, h[i]);
    return out.buffer;
  }
  var subtle = { digest: function (alg, data) {
    var name = (typeof alg === 'string' ? alg : alg && alg.name || '').toUpperCase();
    if (name !== 'SHA-256') return Promise.reject(new Error('lab polyfill: only SHA-256'));
    var u8 = data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    return Promise.resolve(sha256(u8));
  } };
  try { Object.defineProperty(c, 'subtle', { value: subtle, configurable: true }); } catch (e) { /* leave as is */ }
})();

// Lab SSO for the Polaris Console: whenever the app shows its login page, start
// "Sign in with Epireum lab account" automatically (silent if the Keycloak session exists,
// like every other tool). The console routes inside the page (/ → /login without a
// reload), so watch for the login page instead of checking the URL once.
// Open /login?local=1 to use the Client ID / Secret form instead (root, personas).
(function () {
  if (/[?&]local=1\b/.test(location.search)) return;
  // The console keeps its sign-in in memory only, so a deep link (e.g. /catalogs/<name> from
  // the lab's "My catalogs" page) goes /login → sign-in → "/" and loses its target.
  // Remember it, and go there once signed in (in-app navigation, keeps the sign-in).
  var BACK = 'lab_sso_return', p0 = location.pathname;
  if (p0 !== '/' && !/^\/(login|auth\/callback)\/?$/.test(p0)) sessionStorage.setItem(BACK, p0 + location.search);
  var started = Date.now();
  var t = setInterval(function () {
    var p = location.pathname;
    if (!/\/login\/?$/.test(p)) {                                // signed in (or elsewhere)
      var back = sessionStorage.getItem(BACK);
      if (back && !/^\/auth\/callback/.test(p)) {
        sessionStorage.removeItem(BACK);
        if (p === '/') { history.pushState({}, '', back); window.dispatchEvent(new PopStateEvent('popstate')); }
      }
      if (Date.now() - started > 15000) clearInterval(t);
      return;
    }
    var tried = +sessionStorage.getItem('lab_sso_tried') || 0;          // one try per 30 s — no loop on error
    if (Date.now() - tried < 30000) { clearInterval(t); return; }
    var b = Array.prototype.find.call(document.querySelectorAll('button'), function (x) {
      return /Sign in with Epireum lab account/.test(x.textContent);
    });
    if (b) { sessionStorage.setItem('lab_sso_tried', String(Date.now())); clearInterval(t); b.click(); }
  }, 150);
  // a successful sign-in lands outside /login → allow auto sign-in again next time
  window.addEventListener('load', function () {
    setTimeout(function () { if (!/\/login\/?$/.test(location.pathname)) sessionStorage.removeItem('lab_sso_tried'); }, 4000);
  });
})();
