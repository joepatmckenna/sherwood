export default class BaseElement extends HTMLElement {
  constructor(templateName) {
    super();
    this.templateName = templateName;
    this.attachShadow({ mode: "open" });
    this.interceptSherwoodLinks();
  }

  loadTemplate() {
    const template = document.getElementById(this.templateName);
    return template.content.cloneNode(true);
  }

  interceptSherwoodLinks() {
    this.shadowRoot.addEventListener("click", async (event) => {
      const target = event.target.closest("a");
      if (!target) return;
      const href = target.getAttribute("href");
      const isInternal =
        href.startsWith("/") || !href.startsWith(window.location.origin);
      if (!isInternal) return;
      event.preventDefault();

      if (href === "/sherwood/sign-out") {
        const response = await this.callApi("/sign-out", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (!response?.error) {
          this.dispatchEvent(
            new CustomEvent("sherwood-sign-out", {
              bubbles: true,
              composed: true,
              detail: {},
            })
          );
          this.navigateTo("/sherwood/");
        }
      } else {
        this.navigateTo(href);
      }
    });
  }

  navigateTo(href) {
    this.dispatchEvent(
      new CustomEvent("sherwood-navigate-to", {
        bubbles: true,
        composed: true,
        detail: { href },
      })
    );
  }

  async callApi(route, options = {}) {
    try {
      const response = await fetch(`/sherwood/api${route}`, options);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(`${response.status}: ${data?.error?.detail}`);
      } else {
        return data;
      }
    } catch (error) {
      return { error: error.message || "An unexpected error occurred." };
    }
  }
}
