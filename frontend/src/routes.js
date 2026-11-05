export function getPathForRoute(targetPage, exchangeId = null) {
  switch (targetPage) {
    case "home":
      return "/";
    case "browse":
      return "/browse";
    case "mine":
      return "/mine";
    case "requests":
      return "/requests";
    case "exchanges":
      return exchangeId ? `/exchanges/${exchangeId}` : "/exchanges";
    case "notifications":
      return "/notifications";
    case "profile":
      return "/profile";
    case "login":
      return "/login";
    case "register":
      return "/register";
    default:
      return "/";
  }
}

export function parseLocation(pathname) {
  const clean = (pathname || (typeof window !== "undefined" ? window.location.pathname : "/") || "/")
    .replace(/\/+$/, "")
    .toLowerCase();

  if (clean === "" || clean === "/home") {
    return { page: "home", exchangeId: null };
  }
  if (clean === "/browse") {
    return { page: "browse", exchangeId: null };
  }
  if (clean === "/mine") {
    return { page: "mine", exchangeId: null };
  }
  if (clean === "/requests") {
    return { page: "requests", exchangeId: null };
  }
  if (clean === "/notifications") {
    return { page: "notifications", exchangeId: null };
  }
  if (clean === "/profile") {
    return { page: "profile", exchangeId: null };
  }
  if (clean === "/login") {
    return { page: "login", exchangeId: null };
  }
  if (clean === "/register") {
    return { page: "register", exchangeId: null };
  }

  const exchangeMatch = clean.match(/^\/exchanges(?:\/(\d+))?$/);
  if (exchangeMatch) {
    const exchangeId = exchangeMatch[1] ? Number(exchangeMatch[1]) : null;
    return { page: "exchanges", exchangeId };
  }

  return { page: "home", exchangeId: null };
}
