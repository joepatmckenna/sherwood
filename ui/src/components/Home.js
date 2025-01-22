export const HOME_TAG_NAME = "sherwood-home";
export const HOME_TEMPLATE_NAME = "sherwood-home-template";

import BaseElement from "./BaseElement.js";

export default class Home extends BaseElement {
  constructor() {
    super(HOME_TEMPLATE_NAME);
  }

  connectedCallback() {
    const element = this.loadTemplate();
    this.shadowRoot.replaceChildren(element);
  }
}

customElements.define(HOME_TAG_NAME, Home);
