import api from "./api.js";

export async function registerUser({ username, email, password }) {
  const { data } = await api.post("/auth/register", { username, email, password });
  return data.data;
}

export async function loginUser({ username, password }) {
  const { data } = await api.post("/auth/login", { username, password });
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
