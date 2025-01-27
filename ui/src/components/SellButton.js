export const SELL_TAG_NAME = "sherwood-sell-button";

import BaseButton from "./BaseButton.js";

export default class SellButton extends BaseButton {
  constructor() {
    super();
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    ${this.loadStyle()}
    <button id="sell-open-button">sell</button>
    <div class="modal-overlay" id="sell-modal-overlay">
      <div class="modal">
        <button class="close-button" id="sell-close-button">&times;</button>
        <h2>sell</h2>
        <form id="sell-form">
          <label>symbol:</label><br /> <input type="text" name="symbol" required /><br /><br />
          <label>dollars:</label><br /> <input type="number" name="dollars" required /><br /><br />
          <button type="submit">submit</button><br />
        </form>
        <p class="error" id="sell-error-message"></p>
      </div>
    </div>
    `;
    return template.content.cloneNode(true);
  }

  async connectedCallback() {
    const sellButton = this.loadTemplate();
    this.setupModal(
      sellButton,
      "sell-open-button",
      "sell-close-button",
      "sell-modal-overlay"
    );
    this.setupForm(
      sellButton,
      "sell-form",
      "sell-error-message",
      "sell-modal-overlay",
      "/sell"
    );
    this.shadowRoot.appendChild(sellButton);
  }
}

customElements.define(SELL_TAG_NAME, SellButton);
