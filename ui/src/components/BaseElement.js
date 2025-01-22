export class BaseElement extends HTMLElement {
  constructor(templateName) {
    super();
    this.templateName = templateName;
    this.attachShadow({ mode: "open" });
    this.handleLinks();
  }

  loadTemplate() {
    const template = document.getElementById(this.templateName);
    return template.content.cloneNode(true);
  }

  handleLinks() {
    this.shadowRoot.addEventListener("click", (event) => {
      const link = event.target.closest("a[data-link]");
      if (!link) return;
      event.preventDefault();
      const href = link.getAttribute("href");
      this.navigateTo(href);
    });
  }

  navigateTo(href) {
    this.dispatchEvent(
      new CustomEvent("router-link", {
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
