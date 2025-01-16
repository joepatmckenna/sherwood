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

function makeUserPortfolioHoldingsTable(user, elementId) {
  const userOwnership = user.portfolio.ownership.find(
    (ownership) => ownership.owner_id === user.portfolio.id
  );
  if (!userOwnership) {
    console.error("owner ownership not found");
    return;
  }
  const userOwnershipPercent = userOwnership.percent;

  const userPortfolioHoldingsTable = document.getElementById(elementId);
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");

  const symbol = document.createElement("th");
  symbol.textContent = "symbol";
  headerRow.appendChild(symbol);
  const units = document.createElement("th");
  units.textContent = "units";
  headerRow.appendChild(units);
  thead.appendChild(headerRow);
  table.insertBefore(thead, table.firstChild);

  user.portfolio.holdings.forEach((holding) => {
    const userPortfolioHoldingRow = userPortfolioHoldingsTable.insertRow();
    const symbolCell = userPortfolioHoldingRow.insertCell(0);
    const unitsCell = userPortfolioHoldingRow.insertCell(1);
    const ownerUnits = holding.units * userOwnershipPercent;
    symbolCell.textContent = holding.symbol;
    unitsCell.textContent = `${ownerUnits.toFixed(2)}`;
  });
}

async function load() {
  const user = await getUser();
  await maybeMakeBanner(user);
  return { user };
}
