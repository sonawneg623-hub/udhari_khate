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

  // रक्कम बॉक्स: फक्त अंक, ',' आणि '.'
  var amount = document.querySelector(".amount-input");
  if (amount) {
    amount.addEventListener("input", function () {
      amount.value = amount.value.replace(/[^0-9०-९.,]/g, "");
    });
  }

  // ---------- मोबाईल नंबर: फक्त १० अंक ----------
  var phone = document.getElementById("phoneInput");
  if (phone) {
    var DEV = "०१२३४५६७८९";
    phone.addEventListener("input", function () {
      var out = "";
      for (var i = 0; i < phone.value.length; i++) {
        var ch = phone.value[i], d = DEV.indexOf(ch);
        if (d > -1) out += d;
        else if (ch >= "0" && ch <= "9") out += ch;
      }
      phone.value = out.slice(0, 10);
    });
  }

  // ---------- बोलून ग्राहकाचे नाव (Web Speech API, मराठी) ----------
  var micBtn = document.getElementById("micBtn");
  var nameInput = document.getElementById("nameInput");
  var micStatus = document.getElementById("micStatus");
  if (micBtn && nameInput && micStatus) {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    var rec = null, listening = false, gotText = false;
    var icon = micStatus.querySelector("svg") ? micStatus.querySelector("svg").outerHTML : "";

    function say(text, cls) {
      micStatus.className = "mic-status" + (cls ? " " + cls : "");
      micStatus.innerHTML = icon + " " + text;
    }

    micBtn.addEventListener("click", function () {
      if (!SR) {
        say("या ब्राउझरमध्ये बोलून लिहिण्याची सुविधा नाही. Android वर Chrome वापरा, किंवा नाव टाईप करा.", "err");
        return;
      }
      if (listening && rec) { rec.stop(); return; }

      rec = new SR();
      rec.lang = "mr-IN";
      rec.interimResults = true;
      rec.continuous = false;
      rec.maxAlternatives = 1;
      gotText = false;

      rec.onstart = function () {
        listening = true;
        micBtn.classList.add("on");
        say("ऐकत आहे… आता नाव बोला", "listening");
      };
      rec.onresult = function (ev) {
        var t = "";
        for (var i = 0; i < ev.results.length; i++) t += ev.results[i][0].transcript;
        t = t.replace(/[.।,?!]+$/, "").replace(/\s+/g, " ").trim();
        if (t) { nameInput.value = t; gotText = true; }
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
        gotText = true; // त्रुटी संदेश टिकवण्यासाठी
        say(m[ev.error] || "बोलून लिहिता आले नाही. पुन्हा प्रयत्न करा.", "err");
      };
      rec.onend = function () {
        listening = false;
        micBtn.classList.remove("on");
        if (micStatus.classList.contains("listening")) {
          if (nameInput.value && gotText) say("नाव बरोबर आहे का ते तपासा; चुकले असेल तर दुरुस्त करा.", "ok");
          else say("काही ऐकू आले नाही. पुन्हा माइक दाबून बोला.", "err");
        }
        nameInput.focus();
      };
      try { rec.start(); } catch (err) { say("माइक सुरू करता आला नाही. पुन्हा प्रयत्न करा.", "err"); }
    });
  }
})();
