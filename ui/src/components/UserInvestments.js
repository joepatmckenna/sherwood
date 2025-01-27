export const USER_INVESTMENTS_TAG_NAME = "sherwood-user-investments";

import BaseElement from "./BaseElement.js";

export default class UserInvestments extends BaseElement {
  static get observedAttributes() {
    return ["user-id"];
  }

  constructor() {
    super();
    this.userId = null;
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    <div>
      <table border="1">
        <thead>
          <tr>
            <th>user</th>
            <th>amount invested</th>
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

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "user-id" && oldValue !== newValue) {
      this.userId = newValue;
      this.render();
    }
  }

  async render() {
    const userInvestments = this.loadTemplate();
    const tbody = userInvestments.querySelector("tbody");

    const columns = [
      "amount_invested",
      "value",
      "average_daily_return",
      "lifetime_return",
    ];

    const response = await this.callApi("/user-investments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: this.userId,
        columns: columns,
        sort_by: "amount_invested",
      }),
    });
    if (!response?.error) {
      if (response.rows.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="${
          columns.length + 1
        }">no investments yet</td>`;
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
    this.shadowRoot.replaceChildren(userInvestments);
  }
}

customElements.define(USER_INVESTMENTS_TAG_NAME, UserInvestments);
