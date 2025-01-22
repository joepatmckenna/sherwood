export const SIGN_IN_TAG_NAME = "sherwood-sign-in";
export const SIGN_IN_TEMPLATE_NAME = "sherwood-sign-in-template";

import BaseElement from "./BaseElement.js";

export default class SignIn extends BaseElement {
  constructor() {
    super(SIGN_IN_TEMPLATE_NAME);
  }

  setupForm(signIn) {
    const form = signIn.querySelector("form");
    const errorMessage = signIn.getElementById("error-message");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const formData = new FormData(form);
      const body = Object.fromEntries(formData.entries());

      const response = await this.callApi("/sign-in", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (response?.error) {
        errorMessage.textContent = response.error;
      } else {
        this.dispatchEvent(
          new CustomEvent("sherwood-sign-in", {
            bubbles: true,
            composed: true,
            detail: {},
          })
        );
        this.navigateTo(response.redirect_url);
      }
    });
  }

  async connectedCallback() {
    const signIn = this.loadTemplate();
    this.setupForm(signIn);
    this.shadowRoot.replaceChildren(signIn);
  }
}

customElements.define(SIGN_IN_TAG_NAME, SignIn);
