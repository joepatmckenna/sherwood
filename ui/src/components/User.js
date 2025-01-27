export const USER_TAG_NAME = "sherwood-user";

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
    this.portfolioId = userId;
  }

  formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    const day = date.getDate();
    return `${month} ${day}, ${year}`;
  }

  loadTemplate() {
    const template = document.createElement("template");
    template.innerHTML = `
    <h1 id="display-name"></h1>
    <div>
      <span id="member-since"></span><br />
      <span id="email-verified"></span>
    </div>
    <div id="holdings"> </div>
    <div id="investors"> </div>
    <div id="investments"> </div>
    `;
    return template.content.cloneNode(true);
  }

  async connectedCallback() {
    const user = this.loadTemplate();

    let displayName;

    const response = await this.callApi(`/user/${this.userId}`);
    if (!response?.error) {
      displayName = response.display_name;
      user.getElementById("display-name").innerText = displayName;
      user.getElementById("member-since").innerText =
        "joined " + this.formatTimestamp(response.created);
      user.getElementById("email-verified").innerText =
        "email " + (response.is_verified ? "verified" : "unverified");
    }

    user.getElementById("holdings").innerHTML = `
      <h2>fund managed by ${displayName || "this user"}</h2>
      <div id="holdings-controls">
      </div>
      <div>
        <sherwood-portfolio-holdings portfolio-id="${this.portfolioId}">
        </sherwood-portfolio-holdings>
      </div>`;

    user.getElementById("investors").innerHTML = `
      <h2>investors in this fund</h2>
      <div>
        <sherwood-portfolio-investors portfolio-id="${this.portfolioId}">
      </div>`;

    user.getElementById("investments").innerHTML = `
      <h2>funds ${displayName || "this user"} invests in</h2>
      <div id="investments">
        <sherwood-user-investments user-id="${this.userId}">
        </sherwood-user-investments>
      </div>`;

    const u = await this.callApi("/user");
    if (!u?.error) {
      if (`${u.id}` === `${this.userId}`) {
        user.querySelector("#holdings-controls").innerHTML = `
        <sherwood-buy-button> </sherwood-buy-button>
        <sherwood-sell-button> </sherwood-sell-button>
        <br/><br/>
        `;
      } else {
        user.querySelector("#holdings-controls").innerHTML = `
        <sherwood-invest-button> </sherwood-invest-button>
        <sherwood-divest-button> </sherwood-divest-button>
        <br/><br/>
        `;
      }
    }
    this.shadowRoot.replaceChildren(user);
  }
}

customElements.define(USER_TAG_NAME, User);
