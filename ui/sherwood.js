async function getUser() {
  const x_sherwood_authorization = localStorage.getItem(
    "x_sherwood_authorization"
  );
  if (!x_sherwood_authorization) {
    return null;
  }
  try {
    const response = await fetch("/sherwood/http/user", {
      method: "GET",
      headers: {
        "X-Sherwood-Authorization": x_sherwood_authorization,
      },
    });
    const data = await response.json();
    if (response.ok) {
      return data;
    } else {
      console.error(data);
      return null;
    }
  } catch (error) {
    console.error(error);
    return null;
  }
}

async function maybeMakeBanner(user) {
  const bannerContainer = document.getElementById("bannerContainer");
  if (bannerContainer) {
    const response = await fetch("/sherwood/banner.html");
    const bannerHtml = await response.text();
    bannerContainer.innerHTML = bannerHtml;
    const rightLinks = document.getElementById("rightLinks");
    if (user) {
      const profileLink = document.createElement("a");
      profileLink.href = "/sherwood/profile.html";
      profileLink.textContent = "profile";
      rightLinks.appendChild(profileLink);

      const signOutLink = document.createElement("a");
      signOutLink.href = "/sherwood/index.html";
      signOutLink.textContent = "sign out";
      signOutLink.addEventListener("click", () => {
        localStorage.removeItem("x_sherwood_authorization");
      });
      rightLinks.appendChild(signOutLink);
    } else {
      const signUpLink = document.createElement("a");
      signUpLink.href = "/sherwood/sign-up.html";
      signUpLink.textContent = "sign up";
      rightLinks.appendChild(signUpLink);

      const signInLink = document.createElement("a");
      signInLink.href = "/sherwood/sign-in.html";
      signInLink.textContent = "sign in";
      rightLinks.appendChild(signInLink);
    }
  }
}

async function load() {
  const user = await getUser();
  await maybeMakeBanner(user);
  return { user };
}
