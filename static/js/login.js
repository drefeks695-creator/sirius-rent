if (getToken()) {
  window.location.href = getPostLoginRedirect();
}

const statusEl = document.getElementById("auth-status");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

function showAuthTab(tab) {
  document.querySelectorAll(".auth-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.querySelectorAll(".auth-panel").forEach((panel) => {
    const active = panel.dataset.panel === tab;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
  statusEl.textContent = "";
  statusEl.className = "status";
}

document.querySelectorAll(".auth-tab").forEach((btn) => {
  btn.addEventListener("click", () => showAuthTab(btn.dataset.tab));
});

showAuthTab("login");

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await login(
      document.getElementById("login-username").value.trim(),
      document.getElementById("login-password").value
    );
    window.location.href = getPostLoginRedirect();
  } catch (err) {
    setStatus(statusEl, err.message, false);
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("register-username").value.trim();
  const password = document.getElementById("register-password").value;
  const confirm = document.getElementById("register-password-confirm").value;

  if (password !== confirm) {
    setStatus(statusEl, "Пароли не совпадают", false);
    return;
  }

  try {
    await register(username, password);
    window.location.href = getPostLoginRedirect();
  } catch (err) {
    setStatus(statusEl, err.message, false);
  }
});
