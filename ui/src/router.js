export default class Router {
  constructor(routes) {
    this.routes = routes;
    this.loadRoute(window.location.pathname);
    this.handleLinks();
    this.handleBackAndForward();
  }

  handleLinks() {
    document.body.addEventListener("router-link", (event) => {
      const { href } = event.detail;
      if (!href) return;
      event.preventDefault();
      this.navigateTo(href);
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
    const matchedComponent = this.routes[path] || this.routes["/404"];
    const appDiv = document.getElementById("app");
    appDiv.innerHTML = "";
    const component = document.createElement(matchedComponent);
    appDiv.appendChild(component);
  }
}
