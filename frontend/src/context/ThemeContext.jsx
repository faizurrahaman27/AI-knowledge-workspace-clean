import { createContext, useContext, useEffect, useState } from "react";
import { updateTheme } from "../api/auth";

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(
    () => localStorage.getItem("theme") || "dark"
  );

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const setTheme = (next, { sync = true } = {}) => {
    setThemeState(next);
    if (sync && localStorage.getItem("token")) {
      // Best-effort -- if this fails (e.g. token expired), the local
      // preference still applies for this browser.
      updateTheme(next).catch(() => {});
    }
  };

  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
