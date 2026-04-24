export interface NavigationItem {
  href: string;
  label: string;
}

export const navigation: NavigationItem[] = [
  { href: "/", label: "Vue d’ensemble" },
  { href: "/top/", label: "Top stars" },
  { href: "/categories/", label: "Catégories" },
  { href: "/hosting/", label: "Hébergements" }
];

export function withBase(path = "/"): string {
  const base = import.meta.env.BASE_URL.endsWith("/")
    ? import.meta.env.BASE_URL
    : `${import.meta.env.BASE_URL}/`;
  const cleanedPath = path === "/" ? "" : path.replace(/^\/+/, "");

  return cleanedPath ? `${base}${cleanedPath}` : base;
}

export function isCurrentRoute(currentPath: string, targetPath: string): boolean {
  if (targetPath === "/") {
    return currentPath === "/";
  }

  return currentPath === targetPath || currentPath.startsWith(targetPath);
}
