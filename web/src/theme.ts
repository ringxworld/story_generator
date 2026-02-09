import { useEffect, useState } from "react";

export type ThemeMode = "dark" | "light";

const THEME_STORAGE_KEY = "story_gen.theme";
const DEFAULT_THEME: ThemeMode = "dark";

const normalizeTheme = (raw: string | null): ThemeMode => {
  if (raw === "light") {
    return "light";
  }
  return DEFAULT_THEME;
};

const currentTheme = (): ThemeMode => normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY));

const applyThemeAttribute = (theme: ThemeMode): void => {
  document.documentElement.setAttribute("data-theme", theme);
};

export const initializeTheme = (): ThemeMode => {
  const theme = currentTheme();
  applyThemeAttribute(theme);
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  return theme;
};

export const useThemeMode = (): {
  theme: ThemeMode;
  toggleTheme: () => void;
} => {
  const [theme, setTheme] = useState<ThemeMode>(currentTheme);

  useEffect(() => {
    applyThemeAttribute(theme);
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = (): void => {
    setTheme((value) => (value === "dark" ? "light" : "dark"));
  };

  return {
    theme,
    toggleTheme,
  };
};
