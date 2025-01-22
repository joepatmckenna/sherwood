import Router from "./router.js";

const BASE_ROUTE = "/sherwood";

import Home from "./components/Home.js";
import SignIn from "./components/SignIn.js";
import Profile from "./components/Profile.js";

const routes = {
  [`${BASE_ROUTE}/`]: new Home(),
  [`${BASE_ROUTE}/sign-in`]: new SignIn(),
  [`${BASE_ROUTE}/profile`]: new Profile(),
};

new Router(routes);
