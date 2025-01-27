export const BUY_TAG_NAME = "sherwood-buy-button";

import BaseButton from "./BaseButton.js";

export default class BuyButton extends BaseButton {
  constructor() {
    super();
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    ${this.loadStyle()}
    <button id="buy-open-button">buy</button>
    <div class="modal-overlay" id="buy-modal-overlay">
      <div class="modal">
        <button class="close-button" id="buy-close-button">&times;</button>
        <h2>buy</h2>
        <form id="buy-form">
          <label>symbol:</label><br /> <input type="text" name="symbol" required /><br /><br />
          <label>dollars:</label><br /> <input type="number" name="dollars" required /><br /><br />
          <button type="submit">submit</button><br />
        </form>
        <p class="error" id="buy-error-message"></p>
      </div>
    </div>`;
    return template.content.cloneNode(true);
  }

  async connectedCallback() {
    const buyButton = this.loadTemplate();
    this.setupModal(
      buyButton,
      "buy-open-button",
      "buy-close-button",
      "buy-modal-overlay"
    );
    this.setupForm(
      buyButton,
      "buy-form",
      "buy-error-message",
      "buy-modal-overlay",
      "/buy"
    );
    this.shadowRoot.appendChild(buyButton);
  }
}

customElements.define(BUY_TAG_NAME, BuyButton);
