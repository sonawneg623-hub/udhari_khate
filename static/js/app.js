(function () {
  "use strict";

  // ---------- PWA: service worker ----------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    });
  }

  // PWA: "अ‍ॅप इन्स्टॉल करा" बटण (Android Chrome)
  var deferredPrompt = null;
  var installBtn = document.getElementById("installBtn");
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) installBtn.hidden = false;
  });
  if (installBtn) {
    installBtn.addEventListener("click", function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        installBtn.hidden = true;
      });
    });
  }
  window.addEventListener("appinstalled", function () {
    if (installBtn) installBtn.hidden = true;
  });

  // ---------- डिलीटपूर्वी खात्री + दोनदा सबमिट टाळा ----------
  document.addEventListener("submit", function (e) {
    var form = e.target;
    var msg = form.getAttribute && form.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) {
      e.preventDefault();
      return;
    }
    var btn = form.querySelector && form.querySelector('button[type="submit"]');
    if (btn && !e.defaultPrevented) {
      setTimeout(function () { btn.disabled = true; }, 0);
    }
  });

  document.addEventListener("click", function (e) {
    if (e.target.closest && e.target.closest("[data-print]")) window.print();
    var chip = e.target.closest && e.target.closest(".chip-btn");
    if (chip) {
      var input = document.getElementById("noteInput");
      if (input) { input.value = chip.getAttribute("data-note"); input.focus(); }
    }
  });

  // संदेश आपोआप लपवा
  setTimeout(function () {
    document.querySelectorAll(".flash-success").forEach(function (el) {
      el.style.transition = "opacity .5s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 600);
    });
  }, 4500);

  var DEV = "०१२३४५६७८९";
  function devToAscii(s) {
    return s.replace(/[०-९]/g, function (d) { return DEV.indexOf(d); });
  }

  // रक्कम बॉक्स: फक्त अंक, ',' आणि '.'
  var amount = document.querySelector(".amount-input");
  if (amount) {
    amount.addEventListener("input", function () {
      amount.value = amount.value.replace(/[^0-9०-९.,]/g, "");
    });
  }

  // मोबाईल नंबर: फक्त १० अंक
  var phone = document.getElementById("phoneInput");
  if (phone) {
    phone.addEventListener("input", function () {
      phone.value = devToAscii(phone.value).replace(/[^0-9]/g, "").slice(0, 10);
    });
  }

  // पान क्रमांक: अंक/इंग्रजी अक्षरे/-/ ; मराठी अंक -> इंग्रजी; CAPITAL; कमाल १०
  var pageNo = document.getElementById("pageInput");
  if (pageNo) {
    pageNo.addEventListener("input", function () {
      pageNo.value = devToAscii(pageNo.value).toUpperCase().replace(/[^A-Z0-9\/\-]/g, "").slice(0, 10);
    });
  }

  // ---------- मराठी अंक-शब्द -> अंक (पान क्रमांक बोलताना: "पंधरा" -> 15) ----------
  var NUM_WORDS = ("शून्य,एक,दोन,तीन,चार,पाच,सहा,सात,आठ,नऊ,दहा,अकरा,बारा,तेरा,चौदा,पंधरा,सोळा,सतरा,अठरा,एकोणीस," +
    "वीस,एकवीस,बावीस,तेवीस,चोवीस,पंचवीस,सव्वीस,सत्तावीस,अठ्ठावीस,एकोणतीस," +
    "तीस,एकतीस,बत्तीस,तेहतीस,चौतीस,पस्तीस,छत्तीस,सदतीस,अडतीस,एकोणचाळीस," +
    "चाळीस,एक्केचाळीस,बेचाळीस,त्रेचाळीस,चव्वेचाळीस,पंचेचाळीस,सेहेचाळीस,सत्तेचाळीस,अठ्ठेचाळीस,एकोणपन्नास," +
    "पन्नास,एक्कावन्न,बावन्न,त्रेपन्न,चोपन्न,पंचावन्न,छप्पन्न,सत्तावन्न,अठ्ठावन्न,एकोणसाठ," +
    "साठ,एकसष्ट,बासष्ट,त्रेसष्ट,चौसष्ट,पासष्ट,सहासष्ट,सदुसष्ट,अडुसष्ट,एकोणसत्तर," +
    "सत्तर,एक्काहत्तर,बाहत्तर,त्र्याहत्तर,चौऱ्याहत्तर,पंच्याहत्तर,शहात्तर,सत्याहत्तर,अठ्ठ्याहत्तर,एकोणऐंशी," +
    "ऐंशी,एक्क्याऐंशी,ब्याऐंशी,त्र्याऐंशी,चौऱ्याऐंशी,पंच्याऐंशी,शहाऐंशी,सत्त्याऐंशी,अठ्ठ्याऐंशी,एकोणनव्वद," +
    "नव्वद,एक्क्याण्णव,ब्याण्णव,त्र्याण्णव,चौऱ्याण्णव,पंच्याण्णव,शहाण्णव,सत्त्याण्णव,अठ्ठ्याण्णव,नव्व्याण्णव,शंभर").split(",");
  var NUM = {};
  NUM_WORDS.forEach(function (w, i) { NUM[w] = i; });
  var FILLER = /^(पान|पाना|पानाचा|पानावर|पानाचे|क्रमांक|क्र|नंबर|नंबरचे|नं|पेज|page|number|no)$/i;

  // शोधासाठी बोललेला मजकूर साफ करा: "पान पंधरा" / "पान १५" -> "15"
  function cleanSearch(text) {
    var t = devToAscii(text).replace(/[.।,?!]+/g, " ").replace(/\s+/g, " ").trim();
    var parts = t.split(" ").filter(function (w) { return w && !FILLER.test(w); });
    if (!parts.length) return t;
    if (parts.length === 1 && Object.prototype.hasOwnProperty.call(NUM, parts[0])) return String(NUM[parts[0]]);
    if (parts.length > 1 && parts.every(function (w) { return /^\d$/.test(w); })) return parts.join("");
    return parts.join(" ");
  }

  // ---------- बोलून लिहा (Web Speech API, मराठी): नाव आणि शोध ----------
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;

  function setupMic(btn) {
    var input = document.getElementById(btn.getAttribute("data-mic-for"));
    var status = document.getElementById(btn.getAttribute("data-mic-status"));
    var mode = btn.getAttribute("data-mic-mode") || "name";
    if (!input || !status) return;

    var iconEl = status.querySelector("svg");
    var icon = iconEl ? iconEl.outerHTML : "";
    var idle = status.textContent.trim();
    var rec = null, listening = false, gotText = false, failed = false;

    function say(text, cls) {
      status.className = "mic-status" + (cls ? " " + cls : "");
      status.innerHTML = icon + " ";
      status.appendChild(document.createTextNode(text));
    }

    btn.addEventListener("click", function () {
      if (!SR) {
        say("या ब्राउझरमध्ये बोलून लिहिण्याची सुविधा नाही. Android वर Chrome वापरा, किंवा टाईप करा.", "err");
        return;
      }
      if (listening && rec) { rec.stop(); return; }

      rec = new SR();
      rec.lang = "mr-IN";
      rec.interimResults = true;
      rec.continuous = false;
      rec.maxAlternatives = 1;
      gotText = false;
      failed = false;

      rec.onstart = function () {
        listening = true;
        btn.classList.add("on");
        say(mode === "search" ? "ऐकत आहे… नाव किंवा पान क्रमांक बोला" : "ऐकत आहे… आता नाव बोला", "listening");
      };
      rec.onresult = function (ev) {
        var t = "";
        for (var i = 0; i < ev.results.length; i++) t += ev.results[i][0].transcript;
        t = t.replace(/[.।,?!]+$/, "").replace(/\s+/g, " ").trim();
        if (t) { input.value = mode === "search" ? cleanSearch(t) : t; gotText = true; }
      };
      rec.onerror = function (ev) {
        var m = {
          "not-allowed": "माइकची परवानगी द्या (ब्राउझर सेटिंग्समध्ये माइक Allow करा).",
          "service-not-allowed": "माइकची परवानगी द्या (ब्राउझर सेटिंग्समध्ये माइक Allow करा).",
          "no-speech": "काही ऐकू आले नाही. पुन्हा माइक दाबून बोला.",
          "audio-capture": "माइक सापडला नाही.",
          "network": "इंटरनेट तपासा – बोलून लिहायला इंटरनेट लागते.",
          "language-not-supported": "मराठी भाषा या ब्राउझरमध्ये उपलब्ध नाही."
        };
        failed = true;
        say(m[ev.error] || "बोलून लिहिता आले नाही. पुन्हा प्रयत्न करा.", "err");
      };
      rec.onend = function () {
        listening = false;
        btn.classList.remove("on");
        if (failed) return;
        if (!gotText || !input.value) {
          say("काही ऐकू आले नाही. पुन्हा माइक दाबून बोला.", "err");
          return;
        }
        if (mode === "search" && input.form) {
          say("“" + input.value + "” शोधत आहे…", "ok");
          if (input.form.requestSubmit) input.form.requestSubmit(); else input.form.submit();
        } else {
          say("नाव बरोबर आहे का ते तपासा; चुकले असेल तर दुरुस्त करा.", "ok");
          input.focus();
        }
      };
      try { rec.start(); } catch (err) { say("माइक सुरू करता आला नाही. पुन्हा प्रयत्न करा.", "err"); }
    });

    // शोध पान उघडल्यावर स्थिती पुन्हा मूळ मजकुरावर
    if (!status.textContent.trim()) say(idle || "", "");
  }

  document.querySelectorAll("[data-mic-for]").forEach(setupMic);
})();
