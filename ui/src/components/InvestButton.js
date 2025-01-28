export const INVEST_TAG_NAME = "sherwood-invest-button";

import BaseButton from "./BaseButton.js";

export default class InvestButton extends BaseButton {
  constructor() {
    super();
    this.investeePortfolioId = null;
  }

  static get observedAttributes() {
    return ["investee-portfolio-id"];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "investee-portfolio-id" && oldValue !== newValue) {
      this.investeePortfolioId = newValue;
    }
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
          <input type="number" id="investee-portfolio-id-input" name="investee_portfolio_id" required /><br /><br />
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
    if (this.investeePortfolioId != null) {
      const input = investButton.querySelector("#investee-portfolio-id-input");
      input.value = this.investeePortfolioId;
      input.disabled = true;
    }
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
