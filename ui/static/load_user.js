const sherwood = document.getElementById("sherwood");

let user = null;

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
  if (!response?.error) {
    user = response;
  }
  sherwood.dispatchEvent(new CustomEvent("user", { detail: user }));
}

window.onload = getUser;
