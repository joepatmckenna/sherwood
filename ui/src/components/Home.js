export const HOME_ELEMENT_NAME = "sherwood-home";
export const HOME_TEMPLATE_NAME = "sherwood-home-template";

import { BaseElement } from "./BaseElement.js";

export class Home extends BaseElement {
  constructor() {
    super(HOME_TEMPLATE_NAME);
  }

  connectedCallback() {
    const element = this.loadTemplate();
    this.shadowRoot.appendChild(element);
  }
}

customElements.define(HOME_ELEMENT_NAME, Home);
