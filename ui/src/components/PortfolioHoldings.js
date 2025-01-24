export const PORTFOLIO_HOLDINGS_TAG_NAME = "sherwood-portfolio-holdings";
export const PORTFOLIO_HOLDINGS_TEMPLATE_NAME =
  "sherwood-portfolio-holdings-template";

import BaseElement from "./BaseElement.js";

export default class PortfolioHoldings extends BaseElement {
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
    const portfolioHoldings = this.loadTemplate(
      PORTFOLIO_HOLDINGS_TEMPLATE_NAME
    );
    const tbody = portfolioHoldings.querySelector("tbody");

    const columns = [
      "units",
      "price",
      "value",
      "average_daily_return",
      "lifetime_return",
    ];

    const response = await this.callApi("/portfolio-holdings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portfolio_id: this.portfolioId,
        columns: columns,
        sort_by: "value",
      }),
    });
    if (!response?.error) {
      if (response.rows.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="${
          columns.length + 1
        }">no holdings yet</td>`;
        tbody.appendChild(tr);
      }
      response.rows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${row.symbol}</td>
          <td>${row.columns["units"].toFixed(1)}</td>
          <td>$${row.columns["price"].toFixed(2)}</td>
          <td>$${row.columns["value"].toFixed(2)}</td>
          <td>$${row.columns["average_daily_return"].toFixed(2)}</td>
          <td>$${row.columns["lifetime_return"].toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
      });
    }
    this.shadowRoot.replaceChildren(portfolioHoldings);
  }
}

customElements.define(PORTFOLIO_HOLDINGS_TAG_NAME, PortfolioHoldings);
