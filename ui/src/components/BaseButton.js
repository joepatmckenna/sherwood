import BaseElement from "./BaseElement.js";

export default class BaseButton extends BaseElement {
  constructor() {
    super();
  }

  loadStyle() {
    return `
    <style>
      .modal-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 999;
      }

      .modal-overlay.active {
        display: block;
      }

      .modal {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 16px;
        z-index: 1000;
        width: 300px;
      }

      .modal .close-button {
        float: right;
      }

      .error {
        color: red;
      }
    </style>`;
  }

  setupModal(button, openButtonId, closeButtonId, overlayId) {
    const openButton = button.querySelector(`#${openButtonId}`);
    const closeButton = button.querySelector(`#${closeButtonId}`);
    const overlay = button.querySelector(`#${overlayId}`);
    openButton.addEventListener("click", () => {
      overlay.classList.add("active");
    });
    closeButton.addEventListener("click", () => {
      overlay.classList.remove("active");
    });
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        overlay.classList.remove("active");
      }
    });
  }

  setupForm(button, formId, errorMessageId, overlayId, route) {
    const form = button.querySelector(`#${formId}`);
    const errorMessage = button.querySelector(`#${errorMessageId}`);
    const overlay = button.querySelector(`#${overlayId}`);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorMessage.textContent = "";

      const formData = new FormData(form);
      const json = Object.fromEntries(formData.entries());

      const response = await this.callApi(route, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(json),
      });

      console.log(response);
      if (!response?.error) {
        overlay.classList.remove("active");
        form.reset();
      } else {
        errorMessage.textContent =
          response?.error?.detail || "An unexpected error occurred.";
      }
    });
  }
}
