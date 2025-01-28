export const PORTFOLIO_HISTORY_TAG_NAME = "sherwood-portfolio-history";

import BaseElement from "./BaseElement.js";

export default class PortfolioHistory extends BaseElement {
  constructor() {
    super();
    this.portfolioId = null;
  }

  static get observedAttributes() {
    return ["portfolio-id"];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "portfolio-id" && oldValue !== newValue) {
      this.portfolioId = newValue;
      this.render();
    }
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    <div>
      <table border="1">
        <thead>
          <tr>
            <th>transaction type</th>
            <th>timestamp</th>
            <th>asset</th>
            <th>dollars</th>
            <th>price</th>
          </tr>
        </thead>
        <tbody> </tbody>
      </table>
    </div>`;
    return template.content.cloneNode(true);
  }

  async render() {
    const portfolioHistory = this.loadTemplate();
    const tbody = portfolioHistory.querySelector("tbody");
    const columns = ["price", "dollars"];

    const response = await this.callApi("/portfolio-history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portfolio_id: this.portfolioId,
        columns: columns,
      }),
    });
    if (!response?.error) {
      if (response.rows.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="${
          columns.length + 3
        }">no transactions yet</td>`;
        tbody.appendChild(tr);
      }
      response.rows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${row.type}</td>
          <td>${row.created}</td>
          <td>${row.asset}</td>
          <td>$${row.columns["dollars"].toFixed(2)}</td>
          <td>${row.columns["price"] ? "$" : ""}${
          row.columns["price"] ? row.columns["price"].toFixed(2) : ""
        }</td>
        `;
        tbody.appendChild(tr);
      });
    }
    this.shadowRoot.replaceChildren(portfolioHistory);
  }
}

customElements.define(PORTFOLIO_HISTORY_TAG_NAME, PortfolioHistory);
