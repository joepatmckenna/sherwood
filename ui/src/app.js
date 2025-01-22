import Router from "./router.js";

const BASE_ROUTE = "/sherwood";

import { HOME_ELEMENT_NAME } from "./components/Home.js";
import { SIGN_IN_ELEMENT_NAME } from "./components/SignIn.js";
import { PROFILE_ELEMENT_NAME } from "./components/Profile.js";

const routes = {
  [`${BASE_ROUTE}/`]: HOME_ELEMENT_NAME,
  [`${BASE_ROUTE}/sign-in`]: SIGN_IN_ELEMENT_NAME,
  [`${BASE_ROUTE}/profile`]: PROFILE_ELEMENT_NAME,
};

new Router(routes);
