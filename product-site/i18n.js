/**
 * English / Traditional Chinese for the product site.
 *
 * The page ships with the English copy inline so it reads correctly before any
 * script runs. Every translatable node carries data-i18n="<key>", and apply()
 * rewrites them from the table below. Keys whose copy needs markup (code spans,
 * bold, a line break) are marked data-i18n-html and set with innerHTML; those
 * strings are static content from this file, never anything a visitor supplies.
 *
 * The choice is remembered in localStorage so a Chinese reader does not have to
 * switch on every visit. Nothing here is sent anywhere.
 */

const LANGS = ["en", "zh"];
const LKEY = "ownvoice.lang";

const STR = {
  en: {
    "doc.title": "OwnVoice — Captions for speech that is hard to understand",
    "doc.desc": "OwnVoice turns unclear Mandarin speech into readable captions. Free, open source, and it runs on your own computer so no audio is uploaded.",
    "lang.other": "中文",
    "lang.label": "Switch to Chinese",

    "nav.hear": "Hear it",
    "nav.where": "Where it helps",
    "nav.use": "How to use",
    "nav.works": "How well it works",
    "nav.ext": "Extension",
    "nav.start": "Get started",

    "hero.eyebrow": "For people with unclear speech",
    "hero.h1": "Say it once.<br />Be understood.",
    "hero.lede": "Illness and surgery can make speech hard for other people to follow, and almost impossible for phones and computers to follow. OwnVoice listens and turns Mandarin speech into text that anyone can read.",
    "hero.cta1": "Hear the difference",
    "hero.cta2": "Get started",
    "hero.cta3": "Try the live demo",
    "hero.note": "Free. Open source. Your voice never leaves your computer.",

    "what.h2": "What it does",
    "what.1h": "You speak",
    "what.1p": "Talk normally into a laptop or phone. No special microphone and no training session first.",
    "what.2h": "It listens",
    "what.2p": "A speech model built for unclear speech turns what you said into Mandarin text, a phrase at a time.",
    "what.3h": "They read",
    "what.3p": "The person you are talking to reads it on the screen, or on a projector in a bigger room.",

    "hear.h2": "Hear the difference",
    "hear.sub": "This is one sentence from a real recording. Use the buttons to hear it get harder to understand, then read what ordinary speech recognition makes of it and what OwnVoice makes of it.",
    "hear.gloss": "“to communicate constructively with the landowner”",
    "hear.clean": "Clear speech",
    "hear.mild": "Mild",
    "hear.mod": "Moderate",
    "hear.sev": "Severe",
    "hear.hint": "As it gets harder, the pitch flattens and the words stretch out. In Mandarin the pitch is what tells two words apart, so that is exactly the part that carries the meaning.",
    "hear.badTop": "Ordinary speech recognition",
    "hear.badPct": "44% wrong",
    "hear.badNote": "The key word is lost. 溝通, meaning communicate, became 構同, which is not a word.",
    "hear.goodPct": "11% wrong",
    "hear.goodNote": "The sentence is readable. One word is still wrong, so this is a real improvement rather than a perfect one.",

    "live.h2": "Try it with your own voice",
    "live.sub": "Press start, allow the microphone, and speak Mandarin. Pause between sentences. Each pause ends a phrase and the text appears below.",
    "live.btn": "Start captions",
    "live.stop": "Stop",
    "live.note": "Your voice is sent to the model, turned into text, and discarded. It is never stored.",
    "live.listening": "listening…",
    "live.nothing": "(nothing heard)",
    "live.unreachable": "Could not reach the model.",
    "live.micDenied": "Microphone permission was denied.",

    "where.h2": "Where it helps",
    "where.sub": "The same tool, used in very ordinary places.",
    "where.1h": "At home",
    "where.1p": "Families stop guessing. Instead of asking someone to repeat themselves four times, the sentence is simply on the screen.",
    "where.2h": "At a medical appointment",
    "where.2p": "A patient can describe their own symptoms instead of relying on a relative to speak for them.",
    "where.3h": "On video calls",
    "where.3p": "The browser extension captions whatever is playing in a tab, so an online consultation or a work meeting is readable live.",
    "where.4h": "At a service counter",
    "where.4p": "Banks, clinics and government offices can read a request rather than turning someone away.",
    "where.5h": "In a classroom or a hall",
    "where.5p": "Full screen mode puts the captions on a projector so a whole room can follow a speaker.",
    "where.6h": "For speech therapy",
    "where.6p": "Therapists get a written record of what was understood, which is hard to judge by ear alone.",

    "use.h2": "How to use it",
    "use.1h": "Open it",
    "use.1p": "Use the website in a browser, or install the extension if you want to caption video calls and other tabs.",
    "use.2h": "Press start and talk",
    "use.2p": "Allow the microphone once. Speak normally and pause between sentences. Each pause ends a phrase and sends it to be read.",
    "use.3h": "Show the screen",
    "use.3p": "Hand over the phone, turn the laptop around, or switch to full screen for a projector. Change the interface to Chinese whenever you like.",

    "works.h2": "How well it works",
    "works.sub": "Plain numbers, measured on speakers the system had never heard before.",
    "works.1b": "41%",
    "works.1s": "fewer mistakes on the hardest speech, compared with ordinary speech recognition",
    "works.2b": "86%",
    "works.2s": "of characters read correctly overall, up from 81%",
    "works.3b": "Under 1s",
    "works.3s": "to caption a second of speech, so captions keep up with talking",
    "works.honest": "<b>Being straight with you.</b> These results were measured on recordings we degraded on purpose to imitate unclear speech, not yet on recordings from patients. It works, and we are honest that clinical testing is the next step rather than something already finished. Accuracy also varies from person to person, so try it before relying on it.",

    "ext.h2": "The Chrome extension",
    "ext.sub": "The website captions your own microphone. The extension also captions the audio of any browser tab, so a video call, an online class or a recorded meeting becomes readable while it plays. A web page cannot do that.",
    "ext.install": "Install it",
    "ext.warn": "It is not in the Chrome Web Store yet, so it installs from a folder. That takes a minute and is completely normal for an extension you build yourself.",
    "ext.s1": "Download the extension below and unzip it. You get a folder called <code>ownvoice-extension</code>.",
    "ext.s2": "Open <code>chrome://extensions</code> and turn on <b>Developer mode</b>, top right.",
    "ext.s3": "Click <b>Load unpacked</b> and choose the <code>ownvoice-extension</code> folder.",
    "ext.s4": "Open the tab you want captioned, then click the OwnVoice icon <i>on that tab</i>.",
    "ext.s5": "Pick <b>Microphone</b> or <b>This tab’s audio</b>, then press start.",
    "ext.btn": "Download the extension (.zip)",
    "ext.src": "View the source",
    "ext.n1h": "Two capture modes",
    "ext.n1p": "Your microphone, or the sound coming out of the tab you are on.",
    "ext.n2h": "English or Chinese",
    "ext.n2p": "Switch the whole panel between English and 中文 at any time.",
    "ext.n3h": "It needs the model running",
    "ext.n3p": "The extension shows the captions but does not contain the model, so the recogniser has to be running somewhere. That can be your own computer.",
    "nav.app": "App",
    "nav.demo": "Live demo",
    "up.h3": "Try it with your own recording",
    "up.p": "Open the live demo, upload a Mandarin recording and get the OwnVoice transcript. It runs our model online on a free server, so it can take up to a minute. With the model running on your own computer, the same page also captions you live and simulates dysarthria on your own voice.",
    "up.btn": "Open the live demo",
    "app.tag": "Coming soon",
    "app.h2": "The OwnVoice app",
    "app.sub": "The extension covers calls on a computer. The app covers everywhere else: at work, at a service counter, at the doctor. Speak, and your words appear on your phone. One tap shows them in large text to the person in front of you.",
    "app.f1h": "Talk",
    "app.f1p": "Live captions in Traditional Chinese, with an English line under each one.",
    "app.f2h": "Show",
    "app.f2p": "One tap turns the last sentence into big text for a coworker, a pharmacist or a clerk.",
    "app.f3h": "Private by default",
    "app.f3p": "Audio is deleted after captioning. History stays on the phone. Sharing recordings for research is off unless you agree.",
    "app.ios": "App Store · coming soon",
    "app.android": "Google Play · coming soon",
    "app.note": "We are building the app now. Until it ships, the website and the Chrome extension work today.",

    "priv.h2": "Your voice stays yours",
    "priv.p": "The speech is processed on your own computer and then discarded. Nothing is uploaded, nothing is stored, and there is no account to create. That is also why a clinic can try it without a data protection review first.",

    "start.h2": "Get started",
    "start.p": "OwnVoice is free and open source. Use it, read how it works, or build on it.",
    "start.btn": "Get the code",
    "start.note": "Mandarin today. Taiwanese Hokkien and Cantonese are next.",
    "foot.lic": "Open source, MIT licensed",
  },

  zh: {
    "doc.title": "OwnVoice — 為難以辨識的語音產生字幕",
    "doc.desc": "OwnVoice 把不清楚的中文語音變成讀得懂的字幕。免費、開放原始碼，而且在你自己的電腦上執行，不會上傳任何聲音。",
    "lang.other": "English",
    "lang.label": "切換為英文",

    "nav.hear": "聽聽差別",
    "nav.where": "能用在哪",
    "nav.use": "怎麼使用",
    "nav.works": "成效如何",
    "nav.ext": "擴充功能",
    "nav.start": "開始使用",

    "hero.eyebrow": "為說話不清楚的人而做",
    "hero.h1": "說一次，<br />就被聽懂",
    "hero.lede": "疾病與手術會讓說話變得難以辨識，對手機和電腦來說更幾乎無法辨識。OwnVoice 會聽，並把中文語音轉成任何人都讀得懂的文字。",
    "hero.cta1": "聽聽差別",
    "hero.cta2": "開始使用",
    "hero.cta3": "試用線上示範",
    "hero.note": "免費。開放原始碼。你的聲音不會離開你的電腦。",

    "what.h2": "它做什麼",
    "what.1h": "你說話",
    "what.1p": "對著筆電或手機正常說話。不需要特殊麥克風，也不必先做訓練。",
    "what.2h": "它聽",
    "what.2p": "為不清楚的語音打造的語音模型，一句一句把你說的話轉成中文文字。",
    "what.3h": "對方讀",
    "what.3p": "跟你說話的人在螢幕上讀，或在較大的場地用投影機讀。",

    "hear.h2": "聽聽差別",
    "hear.sub": "這是一段真實錄音裡的一句話。用按鈕聽它逐漸變得更難辨識，再看一般語音辨識讀成什麼、OwnVoice 讀成什麼。",
    "hear.gloss": "英文意思：“to communicate constructively with the landowner”",
    "hear.clean": "清楚的語音",
    "hear.mild": "輕度",
    "hear.mod": "中度",
    "hear.sev": "重度",
    "hear.hint": "愈嚴重，音高愈平，字音也拉得愈長。中文靠音高分辨不同的字，所以被破壞的正是承載意義的那一部分。",
    "hear.badTop": "一般語音辨識",
    "hear.badPct": "44% 錯誤",
    "hear.badNote": "關鍵詞不見了。意思是溝通的「溝通」變成「構同」，而那不是一個詞。",
    "hear.goodPct": "11% 錯誤",
    "hear.goodNote": "句子讀得懂。還有一個字是錯的，所以這是真實的改善，不是完美的結果。",

    "live.h2": "用你自己的聲音試試",
    "live.sub": "按開始、允許麥克風，然後說中文。句子之間停一下。每次停頓結束一句，文字就會出現在下面。",
    "live.btn": "開始字幕",
    "live.stop": "停止",
    "live.note": "你的聲音送到模型、轉成文字之後就丟掉，不會被保存。",
    "live.listening": "聽取中…",
    "live.nothing": "（沒有聽到內容）",
    "live.unreachable": "無法連上模型。",
    "live.micDenied": "麥克風權限被拒絕。",

    "where.h2": "能用在哪",
    "where.sub": "同一個工具，用在非常日常的地方。",
    "where.1h": "在家",
    "where.1p": "家人不用再猜。不必請人重複四次，句子就在螢幕上。",
    "where.2h": "看診的時候",
    "where.2p": "病人可以自己描述症狀，不必靠家屬代為發言。",
    "where.3h": "視訊通話",
    "where.3p": "瀏覽器擴充功能會為分頁裡播放的聲音產生字幕，所以線上看診或工作會議能即時被讀懂。",
    "where.4h": "在服務櫃台",
    "where.4p": "銀行、診所與公家機關可以讀懂一項請求，而不是把人請回去。",
    "where.5h": "在教室或會場",
    "where.5p": "全螢幕模式把字幕放上投影機，讓整個場地都跟得上講者。",
    "where.6h": "用在語言治療",
    "where.6p": "治療師會拿到一份「被聽懂了什麼」的文字紀錄，這件事光靠耳朵很難判斷。",

    "use.h2": "怎麼使用",
    "use.1h": "打開它",
    "use.1p": "在瀏覽器裡使用網站，或安裝擴充功能，為視訊通話和其他分頁產生字幕。",
    "use.2h": "按開始，然後說話",
    "use.2p": "允許麥克風一次。正常說話，句子之間停一下。每次停頓結束一句，並送出去辨識。",
    "use.3h": "把螢幕給對方看",
    "use.3p": "把手機交過去、把筆電轉過來，或切換到全螢幕給投影機用。介面隨時可以換成英文或中文。",

    "works.h2": "成效如何",
    "works.sub": "直白的數字，在系統從未聽過的說話者上測得。",
    "works.1b": "41%",
    "works.1s": "在最難辨識的語音上，錯誤比一般語音辨識少這麼多",
    "works.2b": "86%",
    "works.2s": "整體字元正確率，從 81% 提升上來",
    "works.3b": "不到 1 秒",
    "works.3s": "處理一秒語音所需的時間，所以字幕跟得上說話",
    "works.honest": "<b>老實說。</b> 這些結果是在我們刻意劣化、用來模擬不清楚語音的錄音上測得的，還不是在病人的錄音上。它有效，而我們也老實說：臨床測試是下一步，不是已經完成的事。準確率也因人而異，所以在依賴它之前請先試用。",

    "ext.h2": "Chrome 擴充功能",
    "ext.sub": "網站為你自己的麥克風產生字幕。擴充功能還能為任何瀏覽器分頁的聲音產生字幕，所以視訊通話、線上課程或錄好的會議在播放時就能被讀懂。一個網頁做不到這件事。",
    "ext.install": "安裝它",
    "ext.warn": "它還沒有上 Chrome 線上應用程式商店，所以要從資料夾安裝。這只要一分鐘，對自己建置的擴充功能來說完全正常。",
    "ext.s1": "下載下方的擴充功能並解壓縮，會得到一個名為 <code>ownvoice-extension</code> 的資料夾。",
    "ext.s2": "開啟 <code>chrome://extensions</code>，打開右上角的<b>開發人員模式</b>。",
    "ext.s3": "點<b>載入未封裝項目</b>，然後選擇 <code>ownvoice-extension</code> 資料夾。",
    "ext.s4": "開啟你想加字幕的分頁，然後<i>在那個分頁上</i>點 OwnVoice 圖示。",
    "ext.s5": "選<b>麥克風</b>或<b>這個分頁的聲音</b>，再按開始。",
    "ext.btn": "下載擴充功能（.zip）",
    "ext.src": "查看原始碼",
    "ext.n1h": "兩種擷取來源",
    "ext.n1p": "你的麥克風，或你所在分頁發出的聲音。",
    "ext.n2h": "英文或中文",
    "ext.n2p": "整個面板隨時可以在 English 與中文之間切換。",
    "ext.n3h": "需要模型正在執行",
    "ext.n3p": "擴充功能顯示字幕，但本身不含模型，所以辨識器必須在某處執行。那可以是你自己的電腦。",
    "nav.app": "App",
    "nav.demo": "線上示範",
    "up.h3": "用你自己的錄音試試看",
    "up.p": "打開線上示範，上傳一段中文錄音，就能看到 OwnVoice 的辨識結果。模型在免費的線上伺服器執行，可能需要一分鐘左右。若在你自己的電腦上執行模型，同一個頁面還能即時為你產生字幕，並用你自己的聲音模擬構音障礙。",
    "up.btn": "打開線上示範",
    "app.tag": "即將推出",
    "app.h2": "OwnVoice 手機 App",
    "app.sub": "擴充功能負責電腦上的通話，App 負責其他所有場合：工作時、服務櫃台前、看醫生時。你說話，文字就出現在手機上。輕點一下，就能用大字給眼前的人看。",
    "app.f1h": "對話",
    "app.f1p": "以繁體中文即時顯示字幕，每一句下方附上英文。",
    "app.f2h": "出示",
    "app.f2p": "輕點一下，把最後一句變成大字，給同事、藥師或櫃台人員看。",
    "app.f3h": "預設保護隱私",
    "app.f3p": "字幕完成後立即刪除錄音。紀錄只存在手機上。除非你同意，否則不會分享錄音作研究用途。",
    "app.ios": "App Store · 即將推出",
    "app.android": "Google Play · 即將推出",
    "app.note": "我們正在開發 App。在它上架之前，網站和 Chrome 擴充功能今天就能使用。",

    "priv.h2": "你的聲音仍然屬於你",
    "priv.p": "語音在你自己的電腦上處理，然後就丟掉。沒有上傳、沒有儲存，也不需要註冊帳號。這也是診所可以先試用、不必先做資料保護審查的原因。",

    "start.h2": "開始使用",
    "start.p": "OwnVoice 免費且開放原始碼。使用它、了解它怎麼運作，或在它之上繼續開發。",
    "start.btn": "取得程式碼",
    "start.note": "今天支援華語。台語與粵語是下一步。",
    "foot.lic": "開放原始碼，MIT 授權",
  },
};

function pick() {
  const q = new URLSearchParams(location.search).get("lang");
  if (LANGS.includes(q)) return q;
  try {
    const v = localStorage.getItem(LKEY);
    if (LANGS.includes(v)) return v;
  } catch (e) {}
  return (navigator.language || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
}

let lang = pick();

/* live.js builds caption lines at runtime and reads its strings through this. */
window.T = (key) => (STR[lang] && STR[lang][key]) || STR.en[key] || key;

function apply() {
  const tbl = STR[lang];
  document.documentElement.lang = lang === "zh" ? "zh-TW" : "en";
  document.title = tbl["doc.title"];
  const meta = document.querySelector('meta[name="description"]');
  if (meta) meta.setAttribute("content", tbl["doc.desc"]);

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const v = tbl[el.dataset.i18n];
    if (v === undefined) return;
    if (el.hasAttribute("data-i18n-html")) el.innerHTML = v;
    else el.textContent = v;
  });

  const btn = document.getElementById("langBtn");
  if (btn) {
    btn.textContent = tbl["lang.other"];
    btn.setAttribute("aria-label", tbl["lang.label"]);
  }
}

/* live.js swaps the record button's key between live.btn and live.stop, then
   asks for a re-render rather than writing the label itself. */
window.applyI18n = apply;

function setLang(next) {
  lang = next;
  try { localStorage.setItem(LKEY, next); } catch (e) {}
  apply();
}

apply();
document.getElementById("langBtn")
  .addEventListener("click", () => setLang(lang === "en" ? "zh" : "en"));
