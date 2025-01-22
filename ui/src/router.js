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

  loadRoute(path) {
    const component = this.routes[path];
    document.getElementById("sherwood").replaceChildren(component);
  }
}
