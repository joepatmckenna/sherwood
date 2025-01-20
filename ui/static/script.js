const sherwood = document.getElementById("sherwood");

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

async function getUser() {
  const response = await callApi("/user");
  let user;
  if (!response?.error) {
    user = response;
  }
  sherwood.dispatchEvent(new CustomEvent("user", { detail: response }));
}

async function getUserById(user_id) {
  const response = await callApi(`/user/${user_id}`);
  if (!response?.error) {
    user = response;
  }
  sherwood.dispatchEvent(new CustomEvent("user", { detail: user }));
}

async function getPortfolio({ portfolio_id }) {
  const response = await callApi("/portfolio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ portfolio_id }),
  });
  if (response?.error) {
    console.error(response);
    return;
  }
  sherwood.dispatchEvent(
    new CustomEvent("portfolio", { detail: response.portfolio })
  );
}

async function getLeaderboard() {
  const response = await callApi("/blob", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      leaderboard: { top_k: 10, sort_by: "gain_or_loss" },
    }),
  });
  if (response?.error) {
    console.error(response);
    return;
  }
  sherwood.dispatchEvent(
    new CustomEvent("leaderboard", { detail: response.blob })
  );
}
