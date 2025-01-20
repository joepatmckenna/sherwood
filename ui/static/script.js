const sherwood = document.getElementById("sherwood");
const AUTHORIZED_USER_EVENT_NAME = "authorizedUser";
const LEADERBOARD_EVENT_NAME = "leaderboard";
const PORTFOLIO_EVENT_NAME = "portfolio";
const USER_EVENT_NAME = "user";

async function callApi(route, options = {}) {
  try {
    const response = await fetch(`/sherwood/api${route}`, options);
    return response.json();
  } catch (error) {
    return {
      error: { detail: error.message || "An unexpected error occurred." },
    };
  }
}

async function emitAuthorizedUser() {
  const user = await callApi("/user");
  if (!user?.error) {
    sherwood.dispatchEvent(
      new CustomEvent(AUTHORIZED_USER_EVENT_NAME, { detail: user })
    );
  } else {
    console.error(user);
  }
}

async function emitUser(user_id) {
  const user = await callApi(`/user/${user_id}`);
  if (!user?.error) {
    sherwood.dispatchEvent(new CustomEvent(USER_EVENT_NAME, { detail: user }));
  } else {
    console.error(user);
  }
}

async function emitLeaderboard() {
  const response = await callApi("/blob", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      leaderboard: { top_k: 10, sort_by: "gain_or_loss" },
    }),
  });
  if (!response?.error) {
    sherwood.dispatchEvent(
      new CustomEvent(LEADERBOARD_EVENT_NAME, { detail: response.blob })
    );
  } else {
    console.error(response);
  }
}

async function emitPortfolio({ portfolio_id }) {
  const response = await callApi("/portfolio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ portfolio_id }),
  });
  if (!response?.error) {
    sherwood.dispatchEvent(
      new CustomEvent(PORTFOLIO_EVENT_NAME, { detail: response.portfolio })
    );
  } else {
    console.error(response);
  }
}

function setupModal(openButtonId, closeButtonId, overlayId) {
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

function setupForm(formId, errorMessageId, overlayId, endpoint) {
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
