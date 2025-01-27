export const SIGN_IN_TAG_NAME = "sherwood-sign-in";
export const SIGN_IN_TEMPLATE_NAME = "sherwood-sign-in-template";

import BaseElement from "./BaseElement.js";

export default class SignIn extends BaseElement {
  constructor({}) {
    super();
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    <h1>sign in</h1>
    <form id="sign-in-form">
      <label for="email">email:</label><br />
      <input type="email" id="email" name="email" required /><br /><br />
      <label for="password">password:</label><br />
      <input type="password" id="password" name="password" required /><br /><br />
      <button type="submit">sign in</button>
    </form>
    <p class="error" id="error-message"></p>`;
    return template.content.cloneNode(true);
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
    const signIn = this.loadTemplate(SIGN_IN_TEMPLATE_NAME);
    this.setupForm(signIn);
    this.shadowRoot.replaceChildren(signIn);
  }
}

customElements.define(SIGN_IN_TAG_NAME, SignIn);
