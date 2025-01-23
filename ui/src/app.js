import Router from "./router.js";

const BASE_ROUTE = "/sherwood";

// import to register custom element
import Leaderboard from "./components/Leaderboard.js";
import UserHoldings from "./components/UserHoldings.js";

import Home from "./components/Home.js";
import SignUp from "./components/SignUp.js";
import SignIn from "./components/SignIn.js";
import Profile from "./components/Profile.js";
import User from "./components/User.js";

const routes = {
  [`${BASE_ROUTE}/`]: Home,
  [`${BASE_ROUTE}/sign-up`]: SignUp,
  [`${BASE_ROUTE}/sign-in`]: SignIn,
  [`${BASE_ROUTE}/profile`]: Profile,
  [`${BASE_ROUTE}/user/:userId`]: User,
};

new Router(routes);
