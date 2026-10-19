(function () {
  "use strict";

  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* Old single-page links (#about, #contact) now have their own URLs; the old site picked English from the saved choice or the browser */
  var legacy = { about: root.getAttribute("data-about"), contact: root.getAttribute("data-contact") };
  var hash = location.hash.slice(1);
  if (legacy[hash]) {
    var en = root.lang === "en";
    if (!en && location.pathname === "/") {
      var saved = null;
      try { saved = localStorage.getItem("yakup-lang"); } catch (e) {}
      en = saved ? saved === "en" : !/^tr/i.test(navigator.language || "tr");
    }
    location.replace(en ? { about: "/en/about/", contact: "/en/contact/" }[hash] : legacy[hash]);
    return;
  }

  /* Mobile menu */
  var nav = document.getElementById("nav");
  var burger = document.getElementById("burger");
  var main = document.querySelector("main");
  var footer = document.getElementById("footer");
  function setMenu(open) {
    nav.classList.toggle("open", open);
    burger.setAttribute("aria-expanded", String(open));
    burger.setAttribute("aria-label", open ? burger.getAttribute("data-close") : burger.getAttribute("data-open"));
    root.style.overflow = open ? "hidden" : "";
    main.inert = open;
    footer.inert = open;
  }
  if (burger && document.getElementById("menu")) burger.addEventListener("click", function () { setMenu(!nav.classList.contains("open")); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && nav.classList.contains("open")) { setMenu(false); burger.focus(); } });
  window.matchMedia("(min-width: 992px)").addEventListener("change", function (m) { if (m.matches) setMenu(false); });

  /* Copy email */
  var copyBtn = document.getElementById("copy-email");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var label = copyBtn.getAttribute("data-copy");
      var done = function (attr) {
        copyBtn.textContent = copyBtn.getAttribute(attr);
        setTimeout(function () { copyBtn.textContent = label; }, 1800);
      };
      var selectIt = function () {
        var r = document.createRange(); r.selectNodeContents(document.getElementById("footer-email"));
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      };
      try {
        navigator.clipboard.writeText("ykpgunduz@icloud.com").then(function () { done("data-copied"); }, function () { selectIt(); done("data-copy-fail"); });
      } catch (e) { selectIt(); done("data-copy-fail"); }
    });
  }

  /* Reveal on scroll, only for blocks that start below the fold */
  var pending = [];
  if (!reduceMotion) {
    document.querySelectorAll("[data-reveal]").forEach(function (el) {
      if (el.getBoundingClientRect().top < window.innerHeight * 0.95) return;
      el.classList.add("will-reveal");
      if (el.getAttribute("data-reveal") === "lg") el.classList.add("lg");
      pending.push(el);
    });
  }
  function checkReveals() {
    if (!pending.length) return;
    var vh = window.innerHeight;
    pending = pending.filter(function (el) {
      if (el.getBoundingClientRect().top < vh * 0.92) {
        el.classList.add("revealed"); el.classList.remove("will-reveal");
        return false;
      }
      return true;
    });
  }

  /* Home: intro words light up while scrolling through the section */
  var intro = document.getElementById("intro");
  var introText = document.getElementById("intro-text");
  var words = [];
  var introCur = 0;
  if (introText && !reduceMotion) {
    var text = introText.textContent;
    introText.textContent = "";
    text.split(/(\s+)/).forEach(function (part) {
      if (!part) return;
      if (/^\s+$/.test(part)) { introText.appendChild(document.createTextNode(part)); return; }
      var s = document.createElement("span"); s.className = "w"; s.textContent = part; introText.appendChild(s); words.push(s);
    });
  }
  function introTarget() {
    var r = intro.getBoundingClientRect();
    var vh = window.innerHeight;
    var mobile = window.innerWidth <= 767;
    var a = mobile ? vh * 0.85 : vh * 0.8;
    var b = mobile ? vh * 0.75 : vh * 0.6;
    return Math.max(0, Math.min(1, (a - r.top) / Math.max(1, a - b + r.height)));
  }
  function paintIntro(p) {
    var n = words.length; if (!n) return;
    var T = 0.5 + 0.1 * (n - 1);
    for (var i = 0; i < n; i++) {
      var local = Math.max(0, Math.min(1, (p * T - i * 0.1) / 0.5));
      words[i].style.opacity = (0.42 + 0.58 * local).toFixed(3);
    }
  }

  /* Home: odometer digits and statements */
  var process = document.getElementById("process");
  var stack = document.getElementById("digit-stack");
  var items = process ? Array.prototype.slice.call(process.querySelectorAll(".p-item")) : [];
  function updateProcess() {
    if (!process) return;
    var vh = window.innerHeight;
    var mobile = window.innerWidth <= 767;
    var a = 0;
    items.forEach(function (it, i) {
      var top = it.getBoundingClientRect().top;
      if (top < vh * 0.4) a = i;
      var st = it.querySelector(".statement");
      if (mobile || i === 0 || reduceMotion) { st.style.opacity = ""; return; }
      var t = Math.max(0, Math.min(1, (vh * 0.9 - top) / (vh * 0.3)));
      st.style.opacity = (0.42 + 0.58 * t).toFixed(3);
    });
    stack.style.transform = "translateY(" + (-a * 100 / items.length) + "%)";
  }

  var ticking = false;
  var firstFrame = true;
  function frame() {
    ticking = false;
    checkReveals();
    if (intro && words.length) {
      var target = introTarget();
      if (firstFrame) introCur = target;
      introCur += (target - introCur) * 0.3;
      if (Math.abs(target - introCur) < 0.001) introCur = target;
      paintIntro(introCur);
      if (Math.abs(target - introCur) > 0.001) requestTick();
    }
    updateProcess();
    firstFrame = false;
  }
  function requestTick() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }
  window.addEventListener("scroll", requestTick, { passive: true });
  window.addEventListener("resize", requestTick);
  requestTick();

  /* Home: services tabs */
  var tabs = Array.prototype.slice.call(document.querySelectorAll("#services .tab"));
  var mTitle = document.getElementById("m-title");
  var mBody = document.getElementById("m-body");
  var mDetail = document.querySelector(".m-detail");
  function syncMobileDetail(i) {
    if (!mTitle) return;
    mTitle.textContent = tabs[i].querySelector(".tab-title").textContent;
    mBody.textContent = tabs[i].querySelector(".tab-p").textContent;
  }
  function reserveDetailHeight() {
    if (!mDetail) return;
    if (getComputedStyle(mDetail).display === "none") { mDetail.style.minHeight = ""; return; }
    var keepT = mTitle.textContent, keepB = mBody.textContent, max = 0;
    mDetail.style.minHeight = "";
    tabs.forEach(function (tab, i) { syncMobileDetail(i); max = Math.max(max, mDetail.offsetHeight); });
    mTitle.textContent = keepT; mBody.textContent = keepB;
    mDetail.style.minHeight = max + "px";
  }
  function selectTab(i, focus) {
    tabs.forEach(function (tab, j) {
      var on = j === i;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      var pane = document.getElementById(tab.getAttribute("aria-controls"));
      pane.classList.toggle("on", on);
      var img = on && pane.querySelector("img[data-lazy]");
      if (img) show(img);
    });
    if (focus) tabs[i].focus();
    syncMobileDetail(i);
  }
  tabs.forEach(function (tab, i) {
    tab.addEventListener("click", function () { selectTab(i, false); });
    tab.addEventListener("keydown", function (e) {
      var k = e.key;
      if (k === "ArrowDown" || k === "ArrowRight") { e.preventDefault(); selectTab((i + 1) % tabs.length, true); }
      else if (k === "ArrowUp" || k === "ArrowLeft") { e.preventDefault(); selectTab((i - 1 + tabs.length) % tabs.length, true); }
      else if (k === "Home") { e.preventDefault(); selectTab(0, true); }
      else if (k === "End") { e.preventDefault(); selectTab(tabs.length - 1, true); }
    });
  });
  if (tabs.length) { reserveDetailHeight(); window.addEventListener("resize", reserveDetailHeight); }

  /* Home: results marquee gets a hidden copy for a seamless loop */
  var tRow = document.getElementById("t-row");
  if (tRow) {
    var copy = tRow.cloneNode(true);
    copy.removeAttribute("id");
    copy.setAttribute("aria-hidden", "true");
    tRow.parentNode.appendChild(copy);
  }

  /* Offscreen images load only when they get close to the viewport */
  var lazy = Array.prototype.slice.call(document.querySelectorAll("img[data-lazy]"));
  function show(img) {
    if (img.getAttribute("data-srcset")) img.srcset = img.getAttribute("data-srcset");
    img.src = img.getAttribute("data-src");
    img.removeAttribute("data-lazy");
  }
  if (lazy.length) {
    if ("IntersectionObserver" in window) {
      var lio = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { lio.unobserve(en.target); show(en.target); } });
      }, { rootMargin: "120px 600px" });
      /* Logos sit in an overflow:hidden strip that clips the observer's side margin, so the strip loads them as one */
      var logoSec = document.querySelector(".logos");
      lazy.forEach(function (img) { if (!logoSec || !logoSec.contains(img)) lio.observe(img); });
      if (logoSec) {
        var lo = new IntersectionObserver(function (en) {
          if (en[0].isIntersecting) { lo.disconnect(); logoSec.querySelectorAll("img[data-lazy]").forEach(show); }
        }, { rootMargin: "300px 0px" });
        lo.observe(logoSec);
      }
    } else lazy.forEach(show);
  }

  /* Home: the reel loads only when it gets close to the viewport */
  var reel = document.getElementById("reel");
  if (reel) {
    var startReel = function () {
      reel.poster = reel.getAttribute("data-poster");
      var src = reel.querySelector("source");
      src.src = src.getAttribute("data-src");
      var track = reel.querySelector("track");
      if (track) track.src = track.getAttribute("data-src");
      reel.load();
      if (reduceMotion) reel.setAttribute("controls", "");
      else { var p = reel.play(); if (p && p.catch) p.catch(function () {}); }
    };
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting) { io.disconnect(); startReel(); }
      }, { rootMargin: "300px" });
      io.observe(reel);
    } else startReel();
  }
})();
