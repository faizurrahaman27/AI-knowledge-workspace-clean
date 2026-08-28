// Mirrors backend/src/utils/language.py's SPEECH_LANG_TAGS -- kept here
// too since the frontend needs this before any API round-trip (e.g. to
// set recognition.lang before the user has even selected a document).
export const SPEECH_LANG_TAGS = {
  en: "en-US", hi: "hi-IN", es: "es-ES", fr: "fr-FR",
  de: "de-DE", "zh-cn": "zh-CN", ar: "ar-SA", pt: "pt-PT",
  ru: "ru-RU", ja: "ja-JP", te: "te-IN", ta: "ta-IN",
  bn: "bn-IN", mr: "mr-IN", gu: "gu-IN", kn: "kn-IN",
  ml: "ml-IN", pa: "pa-IN", ur: "ur-PK", it: "it-IT",
  ko: "ko-KR", tr: "tr-TR", vi: "vi-VN", id: "id-ID",
  nl: "nl-NL", pl: "pl-PL", th: "th-TH",
};

export function getSpeechTag(languageCode) {
  return SPEECH_LANG_TAGS[languageCode] || "en-US";
}

export const LANGUAGE_DISPLAY_NAMES = {
  en: "English", hi: "Hindi", es: "Spanish", fr: "French",
  de: "German", "zh-cn": "Chinese", ar: "Arabic", pt: "Portuguese",
  ru: "Russian", ja: "Japanese", te: "Telugu", ta: "Tamil",
  bn: "Bengali", mr: "Marathi", gu: "Gujarati", kn: "Kannada",
  ml: "Malayalam", pa: "Punjabi", ur: "Urdu", it: "Italian",
  ko: "Korean", tr: "Turkish", vi: "Vietnamese", id: "Indonesian",
  nl: "Dutch", pl: "Polish", th: "Thai",
};

// Finds the best-matching installed voice for a BCP-47 tag. Whether a
// matching voice actually exists depends entirely on the user's OS/browser
// (e.g. Windows ships far fewer non-English voices than macOS/Chrome OS) --
// this can't conjure a voice that isn't installed, it just picks the best
// available one and otherwise falls back to the browser's default.
export function pickVoiceForLang(voices, tag) {
  if (!voices || voices.length === 0) return null;
  const exact = voices.find((v) => v.lang === tag);
  if (exact) return exact;
  const prefix = tag.split("-")[0];
  const partial = voices.find((v) => v.lang.toLowerCase().startsWith(prefix.toLowerCase()));
  return partial || null;
}

export function speakText(text, languageCode) {
  if (!("speechSynthesis" in window)) {
    alert("Voice output isn't supported in this browser.");
    return;
  }
  window.speechSynthesis.cancel();

  const clean = (text || "").replace(/[#*_`>-]/g, "");
  const utterance = new SpeechSynthesisUtterance(clean);

  const tag = getSpeechTag(languageCode);
  utterance.lang = tag;

  const voices = window.speechSynthesis.getVoices();
  const voice = pickVoiceForLang(voices, tag);
  if (voice) utterance.voice = voice;

  window.speechSynthesis.speak(utterance);
}
