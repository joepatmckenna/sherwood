export const LEADERBOARD_TAG_NAME = "sherwood-leaderboard";
export const LEADERBOARD_TEMPLATE_NAME = "sherwood-leaderboard-template";

import BaseElement from "./BaseElement.js";

export default class Leaderboard extends BaseElement {
  constructor() {
    super();
  }

  async render() {
    const leaderboard = this.loadTemplate(LEADERBOARD_TEMPLATE_NAME);
    const tbody = leaderboard.querySelector("tbody");

    const response = await this.callApi("/leaderboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        columns: [
          "assets_under_management",
          "average_daily_return",
          "lifetime_return",
        ],
        sort_by: "lifetime_return",
        top_k: 10,
      }),
    });

    if (!response?.error) {
      response.rows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>
            <a href="/sherwood/user/${row.user_id}">
              ${row.user_display_name}
            </a>
          </td>              
          <td>$${row.columns["assets_under_management"].toFixed(2)}</td>
          <td>$${row.columns["average_daily_return"].toFixed(2)}</td>
          <td>$${row.columns["lifetime_return"].toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
      });
    }
    this.shadowRoot.replaceChildren(leaderboard);
  }

  async connectedCallback() {
    this.render();
  }
}

customElements.define(LEADERBOARD_TAG_NAME, Leaderboard);
