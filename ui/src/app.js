import Router from "./router.js";

// import to register custom element
import Leaderboard from "./components/Leaderboard.js";
import PortfolioHoldings from "./components/PortfolioHoldings.js";
import PortfolioHistory from "./components/PortfolioHistory.js";
import PortfolioInvestors from "./components/PortfolioInvestors.js";
import UserInvestments from "./components/UserInvestments.js";
import BuyButton from "./components/BuyButton.js";
import SellButton from "./components/SellButton.js";
import InvestButton from "./components/InvestButton.js";
import DivestButton from "./components/DivestButton.js";

import Home from "./components/Home.js";
import SignUp from "./components/SignUp.js";
import SignIn from "./components/SignIn.js";
import User from "./components/User.js";

const BASE_ROUTE = "/sherwood";

const routes = {
  [`${BASE_ROUTE}/`]: Home,
  [`${BASE_ROUTE}/sign-up`]: SignUp,
  [`${BASE_ROUTE}/sign-in`]: SignIn,
  [`${BASE_ROUTE}/user/:userId`]: User,
};

new Router(routes);
