export const PORTFOLIO_INVESTORS_TAG_NAME = "sherwood-portfolio-investors";
export const PORTFOLIO_INVESTORS_TEMPLATE_NAME =
  "sherwood-portfolio-investors-template";

import BaseElement from "./BaseElement.js";

export default class PortfolioInvestors extends BaseElement {
  static get observedAttributes() {
    return ["portfolio-id"];
  }

  constructor() {
    super();
    this.portfolioId = null;
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "portfolio-id" && oldValue !== newValue) {
      this.portfolioId = newValue;
      this.render();
    }
  }

  async render() {
    const portfolioInvestors = this.loadTemplate(
      PORTFOLIO_INVESTORS_TEMPLATE_NAME
    );
    const tbody = portfolioInvestors.querySelector("tbody");

    const columns = [
      "amount_invested",
      "value",
      "average_daily_return",
      "lifetime_return",
    ];

    const response = await this.callApi("/portfolio-investors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portfolio_id: this.portfolioId,
        columns: columns,
        sort_by: "amount_invested",
      }),
    });
    if (!response?.error) {
      if (response.rows.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="${
          columns.length + 1
        }">no investors yet</td>`;
        tbody.appendChild(tr);
      }
      response.rows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>
            <a href="/sherwood/user/${row.user_id}">${row.user_display_name}</a>
          </td>
          <td>$${row.columns["amount_invested"].toFixed(2)}</td>
          <td>$${row.columns["value"].toFixed(2)}</td>
          <td>$${row.columns["average_daily_return"].toFixed(2)}</td>
          <td>$${row.columns["lifetime_return"].toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
      });
    }
    this.shadowRoot.replaceChildren(portfolioInvestors);
  }
}

customElements.define(PORTFOLIO_INVESTORS_TAG_NAME, PortfolioInvestors);
