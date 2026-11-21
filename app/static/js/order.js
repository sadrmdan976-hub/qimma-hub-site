(function () {
  "use strict";

  var select = document.querySelector("[data-service-select]");
  var picker = document.querySelector("[data-tpl-picker]");
  var hint = document.querySelector("[data-price-hint]");
  if (!select || !picker) return;

  var templates = window.QH_TEMPLATES || {};
  var keepTemplate = window.QH_SELECTED_TEMPLATE || 0;
  var currency = window.QH_CURRENCY || "د.ل";

  function previewSrc(t) {
    if (!t.image) return t.preview;
    return /^https?:\/\//.test(t.image) ? t.image : "/static/" + t.image;
  }

  function noneCard() {
    return '<label class="tpl-option">' +
      '<input type="radio" name="template_id" value="0" checked>' +
      '<span class="tpl-card">' +
      '<span class="tpl-none">اقترحوا لي التصميم المناسب</span>' +
      '<span>بدون قالب محدد</span>' +
      '</span></label>';
  }

  function render() {
    var sid = select.value;
    if (hint) {
      var opt = select.options[select.selectedIndex];
      if (sid && opt) {
        var price = opt.getAttribute("data-price") || "";
        var note = opt.getAttribute("data-note") || "";
        var unit = opt.getAttribute("data-unit") || "";
        var days = opt.getAttribute("data-days") || "";
        hint.style.display = "inline-flex";
        hint.textContent = note + " " + price + " " + currency + " " + unit + (days ? " · التنفيذ خلال " + days + " يوم" : "");
      } else {
        hint.style.display = "none";
      }
    }

    var list = templates[String(sid)] || [];
    if (!sid) {
      picker.innerHTML = '<div class="center muted" style="grid-column:1/-1;padding:18px 0;font-size:13.5px">اختر الخدمة أولاً لعرض القوالب المتاحة.</div>';
      return;
    }
    if (!list.length) {
      picker.innerHTML = '<div class="center muted" style="grid-column:1/-1;padding:18px 0;font-size:13.5px">لا توجد قوالب منشورة لهذه الخدمة — سنقترح عليك تصميماً مناسباً.</div>' +
        '<input type="hidden" name="template_id" value="0">';
      return;
    }
    var html = noneCard();
    list.forEach(function (t) {
      var checked = String(t.id) === String(keepTemplate) ? "checked" : "";
      html += '<label class="tpl-option">' +
        '<input type="radio" name="template_id" value="' + t.id + '" ' + checked + '>' +
        '<span class="tpl-card">' +
        '<img src="' + previewSrc(t) + '" alt="' + t.title + '" loading="lazy">' +
        '<span>' + t.title + '</span>' +
        '</span></label>';
    });
    picker.innerHTML = html;
    // keepTemplate applies once, then follow user's actual choice
    keepTemplate = 0;
  }

  select.addEventListener("change", render);
  render();

  // deadline minimum = today
  var deadline = document.getElementById("deadline");
  if (deadline) {
    var d = new Date();
    var iso = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
    deadline.min = iso;
  }
})();
