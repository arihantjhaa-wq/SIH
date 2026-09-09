import api from "./api.js";

export async function registerUser({ username, email, password, name, address }) {
  const payload = { username, email, password };
  if (name) payload.name = name;
  if (address) payload.address = address;
  const { data } = await api.post("/auth/register", payload);
  return data.data;
}

export async function loginUser({ username, password }) {
  const { data } = await api.post("/auth/login", { username, password });
  return data.data;
}

export async function developerAccessLogin({ developerKey }) {
  const { data } = await api.post("/auth/developer-access", { developerKey });
  return data.data;
}

export async function getCurrentUser() {
  const { data } = await api.get("/auth/me");
  return data.data;
}

export async function logoutUser() {
  await api.post("/auth/logout");
  return true;
}
