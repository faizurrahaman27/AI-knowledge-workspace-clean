import { useEffect, useState } from "react";

const DISMISSED_KEY = "install_prompt_dismissed";

function isIos() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

function isStandalone() {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showIosTip, setShowIosTip] = useState(false);
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISSED_KEY) === "true"
  );

  useEffect(() => {
    if (isStandalone()) return; // already installed, nothing to show

    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener("beforeinstallprompt", handler);

    if (isIos()) {
      setShowIosTip(true);
    }

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISSED_KEY, "true");
    setDismissed(true);
  };

  const install = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
  };

  if (dismissed || isStandalone() || (!deferredPrompt && !showIosTip)) {
    return null;
  }

  return (
    <div className="bg-blue-900/40 border border-blue-700 rounded-lg px-4 py-3 flex items-center justify-between gap-3 text-sm mb-4">
      <div className="text-slate-200">
        {deferredPrompt ? (
          <>📱 Install this app for quick access from your home screen.</>
        ) : (
          <>
            📱 On iPhone/iPad: tap the Share button, then{" "}
            <strong>"Add to Home Screen"</strong> to install this app.
          </>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {deferredPrompt && (
          <button
            onClick={install}
            className="bg-blue-600 hover:bg-blue-700 px-3 py-1.5 rounded-lg text-white text-xs"
          >
            Install
          </button>
        )}
        <button
          onClick={dismiss}
          className="text-slate-400 hover:text-white text-xs px-2"
          aria-label="Dismiss"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
