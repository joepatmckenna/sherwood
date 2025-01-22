export const LEADERBOARD_TAG_NAME = "sherwood-leaderboard";
export const LEADERBOARD_TEMPLATE_NAME = "sherwood-leaderboard-template";

import BaseElement from "./BaseElement.js";

export default class Leaderboard extends BaseElement {
  constructor() {
    super(LEADERBOARD_TEMPLATE_NAME);
    this.sortBy = "lifetime_return"; // lifetime_return, average_daily_return, assets_under_management
    this.topK = 10;
  }

  async render() {
    const leaderboard = this.loadTemplate();
    const tbody = leaderboard.querySelector("tbody");
    // tbody.textContent = "";

    const selectElement = leaderboard.getElementById("sort-options");
    selectElement.value = this.sortBy;

    leaderboard;
    selectElement.addEventListener("change", async (event) => {
      this.sortBy = event.target.value;
      tbody.textContent = "";
      await this.render();
    });

    const response = await this.callApi("/leaderboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sort_by: this.sortBy,
        top_k: this.topK,
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
          <td>$${row[this.sortBy].toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
      });
    } else {
      console.error(response);
    }

    this.shadowRoot.replaceChildren(leaderboard);
  }

  async connectedCallback() {
    this.render();
  }
}

customElements.define(LEADERBOARD_TAG_NAME, Leaderboard);
