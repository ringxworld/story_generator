const envFlag = (import.meta.env.VITE_OFFLINE_DEMO as string | undefined)?.trim().toLowerCase();

export const isOfflineDemoMode = (): boolean => {
  if (envFlag === "1" || envFlag === "true" || envFlag === "yes") {
    return true;
  }
  if (typeof window === "undefined") {
    return false;
  }
  const params = new URLSearchParams(window.location.search);
  const demoQuery = params.get("demo");
  if (demoQuery === "1" || demoQuery === "true") {
    return true;
  }
  const pagesHost = window.location.hostname.endsWith("github.io");
  const studioPath = window.location.pathname.includes("/studio/");
  return pagesHost && studioPath;
};
