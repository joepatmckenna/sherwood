export const USER_HOLDINGS_TAG_NAME = "sherwood-user-holdings";
export const USER_HOLDINGS_TEMPLATE_NAME = "sherwood-user-holdings-template";

import BaseElement from "./BaseElement.js";

export default class UserHoldings extends BaseElement {
  static get observedAttributes() {
    return ["user-id"];
  }

  constructor() {
    super();
    this.userId = null;
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "user-id" && oldValue !== newValue) {
      this.userId = newValue;
      this.render();
    }
  }

  async render() {
    const userHoldings = this.loadTemplate(USER_HOLDINGS_TEMPLATE_NAME);
    const tbody = userHoldings.querySelector("tbody");

    const response = await this.callApi("/user-holdings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: this.userId,
      }),
    });
    if (!response?.error) {
      response.rows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${row.symbol}</td>
          <td>${row.units.toFixed(2)}</td>
          <td>$${row.value.toFixed(2)}</td>
          <td>$${row.lifetime_return.toFixed(2)} (${(
          100 * row.lifetime_return_percent
        ).toFixed(1)}%)</td>
        `;
        tbody.appendChild(tr);
      });
    }
    this.shadowRoot.replaceChildren(userHoldings);
  }
}

customElements.define(USER_HOLDINGS_TAG_NAME, UserHoldings);
