export const HEADER_ELEMENT_NAME = "sherwood-header";
export const HEADER_TEMPLATE_NAME = "sherwood-header-template";

import { BaseElement } from "./BaseElement.js";

const SIGNED_IN_LINKS = `
<a href="/sherwood/profile" data-link>profile</a>
<a href="/sherwood/sign-out" data-link>sign out</a>
`;

const SIGNED_OUT_LINKS = `
<a href="/sherwood/sign-up" data-link>sign up</a>
<a href="/sherwood/sign-in" data-link>sign in</a>
`;

export class Header extends BaseElement {
  constructor() {
    super(HEADER_TEMPLATE_NAME);
  }

  async connectedCallback() {
    const template = document.getElementById(this.templateName);
    const node = template.content.cloneNode(true);
    const rightLinks = node.getElementById("right-links");
    const user = await this.callApi("/user");
    if (!user?.error) {
      rightLinks.innerHTML = SIGNED_IN_LINKS;
    } else {
      rightLinks.innerHTML = SIGNED_OUT_LINKS;
    }
    this.shadowRoot.appendChild(node);

    document.body.addEventListener("sherwood-sign-in", (event) => {
      this.shadowRoot.getElementById("right-links").innerHTML = SIGNED_IN_LINKS;
    });

    document.body.addEventListener("sherwood-sign-out", (event) => {
      this.shadowRoot.getElementById("right-links").innerHTML =
        SIGNED_OUT_LINKS;
    });
  }
}

customElements.define(HEADER_ELEMENT_NAME, Header);
