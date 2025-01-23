export const HEADER_TAG_NAME = "sherwood-header";
export const HEADER_TEMPLATE_NAME = "sherwood-header-template";

import BaseElement from "./BaseElement.js";

const SIGNED_IN_LINKS = `
<a href="/sherwood/profile">profile</a>
<a href="/sherwood/sign-out">sign out</a>
`;

const SIGNED_OUT_LINKS = `
<a href="/sherwood/sign-up">sign up</a>
<a href="/sherwood/sign-in">sign in</a>
`;

export default class Header extends BaseElement {
  constructor() {
    super();
  }

  async connectedCallback() {
    const template = document.getElementById(HEADER_TEMPLATE_NAME);
    const header = template.content.cloneNode(true);

    const rightLinks = header.getElementById("right-links");

    const user = await this.callApi("/user");
    rightLinks.innerHTML = user?.error ? SIGNED_OUT_LINKS : SIGNED_IN_LINKS;

    document.body.addEventListener("sherwood-sign-in", () => {
      rightLinks.innerHTML = SIGNED_IN_LINKS;
    });

    document.body.addEventListener("sherwood-sign-out", () => {
      rightLinks.innerHTML = SIGNED_OUT_LINKS;
    });

    this.shadowRoot.appendChild(header);
  }
}

customElements.define(HEADER_TAG_NAME, Header);
