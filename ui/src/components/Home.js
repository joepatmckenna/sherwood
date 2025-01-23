export const HOME_TAG_NAME = "sherwood-home";
export const HOME_TEMPLATE_NAME = "sherwood-home-template";

import BaseElement from "./BaseElement.js";

export default class Home extends BaseElement {
  constructor({}) {
    super();
  }

  connectedCallback() {
    const home = this.loadTemplate(HOME_TEMPLATE_NAME);
    this.shadowRoot.replaceChildren(home);
  }
}

customElements.define(HOME_TAG_NAME, Home);
