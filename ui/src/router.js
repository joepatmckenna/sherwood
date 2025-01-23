export default class Router {
  constructor(routes) {
    this.routes = routes;
    this.loadRoute(window.location.pathname);
    this.handleInternalLinks();
    this.handleBackAndForward();
  }

  handleInternalLinks() {
    document.body.addEventListener("sherwood-navigate-to", (event) => {
      event.preventDefault();
      this.navigateTo(event.detail.href);
    });
  }

  handleBackAndForward() {
    window.addEventListener("popstate", () => {
      this.loadRoute(window.location.pathname);
    });
  }

  navigateTo(path) {
    window.history.pushState({}, "", path);
    this.loadRoute(path);
  }

  // loadRoute(path) {
  //   const component = this.routes[path];
  //   document.getElementById("sherwood").replaceChildren(component);
  // }

  loadRoute(path) {
    const component = this.loadComponent(path);
    const sherwood = document.getElementById("sherwood");
    if (!component) {
      sherwood.innerHTML = `<h1>404 - Page Not Found</h1>`;
      return;
    }
    sherwood.replaceChildren(component);
  }

  loadComponent(path) {
    for (const route in this.routes) {
      const paramNames = [];
      const regexPath = route.replace(/:([a-zA-Z0-9]+)/g, (_, param) => {
        paramNames.push(param);
        return "([^/]+)";
      });

      const regex = new RegExp(`^${regexPath}$`);
      const match = path.match(regex);

      if (match) {
        const params = paramNames.reduce((acc, paramName, i) => {
          acc[paramName] = match[i + 1];
          return acc;
        }, {});
        return new this.routes[route](params);
      }
    }

    return null;
  }
}
