export const USER_TAG_NAME = "sherwood-user";
export const USER_TEMPLATE_NAME = "sherwood-user-template";

import BaseElement from "./BaseElement.js";

const months = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export default class User extends BaseElement {
  constructor({ userId }) {
    super();
    this.userId = userId;
  }

  formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    const day = date.getDate();
    return `${month} ${day}, ${year}`;
  }

  async connectedCallback() {
    const user = this.loadTemplate(USER_TEMPLATE_NAME);

    const response = await this.callApi(`/user/${this.userId}`);
    if (!response?.error) {
      user.getElementById("display-name").innerText =
        "User: " + response.display_name;
      user.getElementById("member-since").innerText =
        "joined " + this.formatTimestamp(response.created_at);
      user.getElementById("email-verified").innerText =
        "email " + (response.is_verified ? "verified" : "unverified");
    }

    const userHoldings = document.createElement("sherwood-user-holdings");
    userHoldings.setAttribute("user-id", this.userId);
    user.getElementById("holdings").appendChild(userHoldings);

    this.shadowRoot.replaceChildren(user);
  }
}

customElements.define(USER_TAG_NAME, User);
