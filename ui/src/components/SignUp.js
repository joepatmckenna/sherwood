export const SIGN_UP_TAG_NAME = "sherwood-sign-up";
export const SIGN_UP_TEMPLATE_NAME = "sherwood-sign-up-template";

import BaseElement from "./BaseElement.js";

export default class SignUp extends BaseElement {
  constructor({}) {
    super();
  }

  setupForm(signUp) {
    const form = signUp.querySelector("form");
    const errorMessage = signUp.getElementById("error-message");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const formData = new FormData(form);
      const body = Object.fromEntries(formData.entries());

      const response = await this.callApi("/sign-up", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (response?.error) {
        errorMessage.textContent = response.error;
      } else {
        this.navigateTo(response.redirect_url);
      }
    });
  }

  setupDisplayNameValidator(signUp) {
    const displayNameInput = signUp.getElementById("display-name");
    const displayNameRequirements = signUp.getElementById(
      "display-name-requirements"
    );
    let socket;

    displayNameInput.addEventListener("input", (event) => {
      const displayName = event.target.value;
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(displayName);
      }
    });

    function updateDisplayNameRequirements(reasons) {
      displayNameRequirements.innerHTML = "";
      reasons.forEach((reason) => {
        const li = document.createElement("li");
        li.textContent = reason;
        li.className = "error";
        displayNameRequirements.appendChild(li);
      });
    }

    function connectToValidateDisplayNameWebSocket() {
      socket = new WebSocket("/sherwood/api/validate-display-name");
      socket.onmessage = (event) => {
        updateDisplayNameRequirements(JSON.parse(event.data).reasons);
      };
      socket.onclose = () => {
        setTimeout(connectToValidateDisplayNameWebSocket, 1000);
      };
    }

    connectToValidateDisplayNameWebSocket();
  }

  setupPasswordValidator(signUp) {
    const passwordInput = signUp.getElementById("password");
    const passwordRequirements = signUp.getElementById("password-requirements");
    let socket;

    passwordInput.addEventListener("input", (event) => {
      const password = event.target.value;
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(password);
      }
    });

    function updatePasswordRequirements(reasons) {
      passwordRequirements.innerHTML = "";
      reasons.forEach((reason) => {
        const li = document.createElement("li");
        li.textContent = reason;
        li.className = "error";
        passwordRequirements.appendChild(li);
      });
    }

    function connectToValidatePasswordWebSocket() {
      socket = new WebSocket("/sherwood/api/validate-password");
      socket.onmessage = (event) => {
        updatePasswordRequirements(JSON.parse(event.data).reasons);
      };
      socket.onclose = () => {
        setTimeout(connectToValidatePasswordWebSocket, 1000);
      };
    }

    connectToValidatePasswordWebSocket();
  }

  async connectedCallback() {
    const signUp = this.loadTemplate(SIGN_UP_TEMPLATE_NAME);
    this.setupForm(signUp);
    this.setupDisplayNameValidator(signUp);
    this.setupPasswordValidator(signUp);
    this.shadowRoot.replaceChildren(signUp);
  }
}

customElements.define(SIGN_UP_TAG_NAME, SignUp);
