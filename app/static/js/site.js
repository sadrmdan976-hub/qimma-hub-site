(function () {
  "use strict";

  // mobile nav
  var mobileNav = document.querySelector("[data-mobile-nav]");
  document.querySelectorAll("[data-nav-open]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      mobileNav.classList.add("is-open");
      document.body.style.overflow = "hidden";
    });
  });
  function closeNav() {
    if (!mobileNav) return;
    mobileNav.classList.remove("is-open");
    document.body.style.overflow = "";
  }
  document.querySelectorAll("[data-nav-close]").forEach(function (btn) {
    btn.addEventListener("click", closeNav);
  });
  if (mobileNav) {
    mobileNav.addEventListener("click", function (e) {
      if (e.target === mobileNav) closeNav();
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeNav();
      closeLightbox();
    }
  });

  // reveal on scroll
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
  }

  // lightbox
  var lightbox = document.querySelector("[data-lightbox]");
  var lightboxImg = lightbox ? lightbox.querySelector("img") : null;
  function openLightbox(src, alt) {
    if (!lightbox || !lightboxImg) return;
    lightboxImg.src = src;
    lightboxImg.alt = alt || "";
    lightbox.classList.add("is-open");
    document.body.style.overflow = "hidden";
  }
  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove("is-open");
    lightboxImg.src = "";
    document.body.style.overflow = "";
  }
  document.querySelectorAll("[data-lightbox-src]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      openLightbox(el.getAttribute("data-lightbox-src"), el.getAttribute("data-lightbox-title"));
    });
  });
  if (lightbox) {
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox || e.target.closest("[data-lightbox-close]")) closeLightbox();
    });
  }

  // copy buttons
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy");
      var done = function () {
        var old = btn.innerHTML;
        btn.innerHTML = "تم النسخ ✓";
        setTimeout(function () { btn.innerHTML = old; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () {});
      } else {
        var ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); done(); } catch (err) {}
        document.body.removeChild(ta);
      }
    });
  });

  // file input label
  document.querySelectorAll("[data-file-input]").forEach(function (input) {
    input.addEventListener("change", function () {
      var drop = input.closest("[data-file-drop]");
      var nameEl = drop ? drop.querySelector("[data-file-name]") : null;
      if (nameEl) nameEl.textContent = input.files && input.files[0] ? input.files[0].name : "";
    });
  });
})();
