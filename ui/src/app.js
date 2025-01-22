import Router from "./router.js";

const BASE_ROUTE = "/sherwood";

import Home from "./components/Home.js";
import SignUp from "./components/SignUp.js";
import SignIn from "./components/SignIn.js";
import Profile from "./components/Profile.js";

// import to register custom element
import Leaderboard from "./components/Leaderboard.js";

const routes = {
  [`${BASE_ROUTE}/`]: new Home(),
  [`${BASE_ROUTE}/sign-up`]: new SignUp(),
  [`${BASE_ROUTE}/sign-in`]: new SignIn(),
  [`${BASE_ROUTE}/profile`]: new Profile(),
};

new Router(routes);
