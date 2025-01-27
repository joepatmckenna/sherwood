export function setupModal(openButtonId, closeButtonId, overlayId) {
  const openButton = document.getElementById(openButtonId);
  const closeButton = document.getElementById(closeButtonId);
  const overlay = document.getElementById(overlayId);
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

export function setupForm(formId, errorMessageId, overlayId, endpoint) {
  const form = document.getElementById(formId);
  const errorMessage = document.getElementById(errorMessageId);
  const overlay = document.getElementById(overlayId);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorMessage.textContent = "";

    const formData = new FormData(form);
    const json = Object.fromEntries(formData.entries());

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(json),
      });
      if (response.ok) {
        overlay.classList.remove("active");
        form.reset();
        location.reload();
      } else {
        const data = await response.json();
        errorMessage.textContent = data?.error?.detail || UNEXPECTED_ERROR;
      }
    } catch (error) {
      console.error(error);
      errorMessage.textContent = error.message || UNEXPECTED_ERROR;
    }
  });
}
