import api from "./axios";

export async function register(data) {
  const response = await api.post("/auth/register", data);
  return response.data;
}

export async function login(data) {
  const formData = new URLSearchParams();
  formData.append("username", data.email);
  formData.append("password", data.password);

  const response = await api.post("/auth/token", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  return response.data;
}

export async function loginWithGoogle(idToken) {
  const response = await api.post("/auth/google", { id_token: idToken });
  return response.data;
}

export async function getMe() {
  const response = await api.get("/auth/me");
  return response.data;
}

export async function changePassword(currentPassword, newPassword) {
  const response = await api.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
}

export async function forgotPassword(email) {
  const response = await api.post("/auth/forgot-password", { email });
  return response.data;
}

export async function resetPassword(email, token, newPassword) {
  const response = await api.post("/auth/reset-password", {
    email,
    token,
    new_password: newPassword,
  });
  return response.data;
}

export async function logoutEverywhere() {
  const response = await api.post("/auth/logout-everywhere");
  return response.data;
}

export async function updateTheme(theme) {
  const response = await api.patch("/auth/theme", { theme });
  return response.data;
}

export function saveTokens(data) {
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
}
