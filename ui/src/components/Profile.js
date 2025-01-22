export const PROFILE_TAG_NAME = "sherwood-profile";
export const PROFILE_TEMPLATE_NAME = "sherwood-profile-template";

import BaseElement from "./BaseElement.js";

export default class Profile extends BaseElement {
  constructor() {
    super(PROFILE_TEMPLATE_NAME);
  }

  async connectedCallback() {
    const element = this.loadTemplate();
    this.shadowRoot.replaceChildren(element);
  }
}

customElements.define(PROFILE_TAG_NAME, Profile);
