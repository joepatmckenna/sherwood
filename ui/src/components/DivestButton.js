export const DIVEST_TAG_NAME = "sherwood-divest-button";

import BaseButton from "./BaseButton.js";

export default class DivestButton extends BaseButton {
  constructor() {
    super();
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    ${this.loadStyle()}
    <button id="divest-open-button">divest</button>
    <div class="modal-overlay" id="divest-modal-overlay">
    <div class="modal">
      <button class="close-button" id="divest-close-button"> &times; </button>
      <h2>divest</h2>
      <form id="divest-form">
        <label>portfolio id:</label><br />
        <input type="number" step="1" min="1" name="investee_portfolio_id" required /><br /><br />
        <label>dollars:</label><br />
        <input type="number" name="dollars" required /><br /><br />
        <button type="submit">submit</button><br />
      </form>
      <p class="error" id="divest-error-message"></p>
    </div>
  </div>`;
    return template.content.cloneNode(true);
  }

  async connectedCallback() {
    const divestButton = this.loadTemplate();
    this.setupModal(
      divestButton,
      "divest-open-button",
      "divest-close-button",
      "divest-modal-overlay"
    );
    this.setupForm(
      divestButton,
      "divest-form",
      "divest-error-message",
      "divest-modal-overlay",
      "/divest"
    );
    this.shadowRoot.appendChild(divestButton);
  }
}

customElements.define(DIVEST_TAG_NAME, DivestButton);
