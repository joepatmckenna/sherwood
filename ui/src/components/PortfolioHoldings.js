export const PORTFOLIO_HOLDINGS_TAG_NAME = "sherwood-portfolio-holdings";

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

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `<div>
        <span id="cash"></span>
        <table border="1">
          <thead>
            <tr>
              <th>symbol</th>
              <th>units</th>
              <th>price</th>
              <th>value</th>
              <th>average daily return</th>
              <th>lifetime return</th>
            </tr>
          </thead>
          <tbody>
          </tbody>
        </table>
      </div>`;
    return template.content.cloneNode(true);
  }

  async render() {
    const portfolioHoldings = this.loadTemplate();
    const cashElement = portfolioHoldings.querySelector("#cash");
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
      if (response.rows.length === 1) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="${
          columns.length + 1
        }">no holdings yet</td>`;
        tbody.appendChild(tr);
      }
      response.rows.forEach((row) => {
        if (row.symbol === "USD") {
          cashElement.innerText = `cash: $${row.columns["units"].toFixed(2)}`;
        } else {
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
        }
      });
    }
    this.shadowRoot.replaceChildren(portfolioHoldings);
  }
}

customElements.define(PORTFOLIO_HOLDINGS_TAG_NAME, PortfolioHoldings);
