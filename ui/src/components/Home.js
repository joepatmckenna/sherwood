export const HOME_TAG_NAME = "sherwood-home";

import BaseElement from "./BaseElement.js";

export default class Home extends BaseElement {
  constructor({}) {
    super();
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    <sherwood-leaderboard> </sherwood-leaderboard>
    `;
    return template.content.cloneNode(true);
  }

  connectedCallback() {
    const home = this.loadTemplate();
    this.shadowRoot.replaceChildren(home);
  }
}

customElements.define(HOME_TAG_NAME, Home);
