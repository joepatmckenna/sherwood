export const PROFILE_TAG_NAME = "sherwood-profile";
export const PROFILE_TEMPLATE_NAME = "sherwood-profile-template";

import BaseElement from "./BaseElement.js";

export default class Profile extends BaseElement {
  constructor({}) {
    super();
  }

  async connectedCallback() {
    const profile = this.loadTemplate(PROFILE_TEMPLATE_NAME);
    this.shadowRoot.replaceChildren(profile);
  }
}

customElements.define(PROFILE_TAG_NAME, Profile);
