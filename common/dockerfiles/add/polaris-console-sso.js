// Lab SSO for the Polaris Console: whenever the app shows its login page, start
// "Sign in with Epireum lab account" automatically (silent if the Keycloak session exists,
// like every other tool). The console routes inside the page (/ → /login without a
// reload), so watch for the login page instead of checking the URL once.
// Open /login?local=1 to use the Client ID / Secret form instead (root, personas).
(function () {
  if (/[?&]local=1\b/.test(location.search)) return;
  var started = Date.now();
  var t = setInterval(function () {
    if (!/\/login\/?$/.test(location.pathname)) {              // signed in (or elsewhere)
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
