export const PROFILE_ELEMENT_NAME = "sherwood-profile";
export const PROFILE_TEMPLATE_NAME = "sherwood-profile-template";

import { BaseElement } from "./BaseElement.js";

export class Profile extends BaseElement {
  constructor() {
    super(PROFILE_TEMPLATE_NAME);
  }

  async connectedCallback() {
    const element = this.loadTemplate();
    this.shadowRoot.appendChild(element);
  }
}

customElements.define(PROFILE_ELEMENT_NAME, Profile);
