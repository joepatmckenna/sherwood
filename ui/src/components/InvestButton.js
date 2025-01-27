export const INVEST_TAG_NAME = "sherwood-invest-button";

import BaseButton from "./BaseButton.js";

export default class InvestButton extends BaseButton {
  constructor() {
    super();
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    ${this.loadStyle()}
    <button id="invest-open-button">invest</button>
    <div class="modal-overlay" id="invest-modal-overlay">
      <div class="modal">
        <button class="close-button" id="invest-close-button"> &times; </button>
        <h2>invest</h2>
        <form id="invest-form">
          <label>portfolio id:</label><br />
          <input type="number" step="1" min="1" name="investee_portfolio_id" required /><br /><br />
          <label>dollars:</label><br />
          <input type="number" name="dollars" required /><br /><br />
          <button type="submit">submit</button><br />
        </form>
        <p class="error" id="invest-error-message"></p>
      </div>
    </div>`;
    return template.content.cloneNode(true);
  }

  async connectedCallback() {
    const investButton = this.loadTemplate();
    this.setupModal(
      investButton,
      "invest-open-button",
      "invest-close-button",
      "invest-modal-overlay"
    );
    this.setupForm(
      investButton,
      "invest-form",
      "invest-error-message",
      "invest-modal-overlay",
      "/invest"
    );
    this.shadowRoot.appendChild(investButton);
  }
}

customElements.define(INVEST_TAG_NAME, InvestButton);
