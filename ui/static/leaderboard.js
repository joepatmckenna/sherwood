class PortfolioLeaderboard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.sortBy = "lifetime_return"; // lifetime_return, average_daily_return, fund_size
    this.topK = 10;
  }

  async connectedCallback() {
    this.shadowRoot.innerHTML = `
    <div>
      <h2>Leaderboard</h2>
      <label for="sort-options">sort by: </label>
      <select id="sort-options">
        <option value="lifetime_return">Lifetime Return</option>
        <option value="average_daily_return">Average Daily Return</option>
        <option value="assets_under_management">Assets Under Management</option>
      </select>    
      <table>
        <thead>
          <tr>
            <th>user</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="table-body">
        </tbody>
      </table>
    </div>
    `;

    this.render();

    this.shadowRoot
      .querySelector("#sort-options")
      .addEventListener("change", (e) => {
        this.sortBy = e.target.value;
        this.render();
      });
  }

  async render() {
    const tbody = this.shadowRoot.querySelector("#table-body");
    tbody.textContent = "";

    try {
      const response = await fetch(`/sherwood/api/leaderboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sort_by: this.sortBy,
          top_k: this.topK,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error?.detail || "An unknown error occurred.");
      } else {
        data.rows.forEach((row) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>
              <a href="/sherwood/user/${row.user_id}">
                ${row.user_display_name}</td>
              </a>
            <td>$${row[this.sortBy].toFixed(2)}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    } catch (error) {
      console.error(error.message);
    }
  }
}

customElements.define("portfolio-leaderboard", PortfolioLeaderboard);
