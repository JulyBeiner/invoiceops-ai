import { clearToken, getToken, setToken } from "./api";

export const initialStore = () => {
  return {
    token: getToken(),
    user: null,
    toast: null,
  };
};

export default function storeReducer(store, action = {}) {
  switch (action.type) {
    case "login":
      setToken(action.payload.token);
      return { ...store, token: action.payload.token, user: action.payload.user };

    case "set_user":
      return { ...store, user: action.payload };

    case "logout":
      clearToken();
      return { ...store, token: null, user: null };

    case "toast":
      return { ...store, toast: action.payload };

    default:
      throw Error("Unknown action.");
  }
}