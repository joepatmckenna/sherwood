export const HEADER_TAG_NAME = "sherwood-header";

import BaseElement from "./BaseElement.js";

const SIGNED_OUT_LINKS = `
<a href="/sherwood/sign-up">sign up</a>
<a href="/sherwood/sign-in">sign in</a>
`;

export default class Header extends BaseElement {
  constructor() {
    super();
  }

  signedInLinks(user_id) {
    return `
    <a href="/sherwood/user/${user_id}">profile</a>
    <a href="/sherwood/sign-out">sign out</a>
    `;
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    <style>
      nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      nav div {
        display: flex;
        gap: 8px;
      }
    </style>

    <nav>
      <div class="links">
        <a href="/sherwood/" data-link>leaderboard</a>
      </div>
      <div class="links" id="right-links"> </div>
    </nav>`;
    return template.content.cloneNode(true);
  }

  async connectedCallback() {
    const header = this.loadTemplate();
    const rightLinks = header.querySelector("#right-links");
    const user = await this.callApi("/user");
    if (user?.error) {
      rightLinks.innerHTML = SIGNED_OUT_LINKS;
    } else {
      rightLinks.innerHTML = this.signedInLinks(user.id);
    }
    document.body.addEventListener("sherwood-sign-in", () => {
      rightLinks.innerHTML = this.signedInLinks(user.id);
    });
    document.body.addEventListener("sherwood-sign-out", () => {
      rightLinks.innerHTML = SIGNED_OUT_LINKS;
    });
    this.shadowRoot.appendChild(header);
  }
}

customElements.define(HEADER_TAG_NAME, Header);
