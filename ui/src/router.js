export default class Router {
  constructor(routes) {
    this.routes = routes;
    this.loadRoute(window.location.pathname);
    this.handleLinks();
    this.handleBackAndForward();
  }

  handleLinks() {
    document.body.addEventListener("sherwood-navigate-to", (event) => {
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
    const component = this.routes[path];
    const sherwood = document.getElementById("sherwood");
    sherwood.innerHTML = "";
    sherwood.appendChild(component);
  }
}
