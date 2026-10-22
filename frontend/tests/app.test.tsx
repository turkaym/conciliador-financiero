import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App from "../src/App";
import { AuthProvider } from "../src/auth";

function renderApp(path = "/login") {
  window.history.pushState({}, "", path);
  return render(<BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>);
}

const validResponse = {
  access_token: "signed-token",
  token_type: "bearer",
  expires_in: 1800,
  user: { id: 1, email: "demo@conciliador.local" },
};

describe("frontend authentication flow", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => cleanup());

  it("logs in the demo user and renders the protected shell", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(new Response(JSON.stringify(validResponse), { status: 200 }));
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("Email"), "demo@conciliador.local");
    await user.type(screen.getByLabelText("Contraseña"), "Demo1234!");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("heading", { name: "Bienvenido al conciliador" })).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("conciliador.session")!)).toMatchObject({ accessToken: "signed-token" });
  });

  it("displays the API error for invalid credentials", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(new Response(JSON.stringify({ message: "Invalid email or password" }), { status: 401 }));
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("Email"), "demo@conciliador.local");
    await user.type(screen.getByLabelText("Contraseña"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
    expect(screen.getByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("restores a valid persisted session on a protected route", async () => {
    localStorage.setItem("conciliador.session", JSON.stringify({
      accessToken: "persisted-token",
      user: validResponse.user,
      expiresAt: Date.now() + 60_000,
    }));
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Bienvenido al conciliador" })).toBeInTheDocument();
    expect(screen.getByText("demo@conciliador.local")).toBeInTheDocument();
  });

  it("redirects an unauthenticated visitor from protected navigation", async () => {
    renderApp("/");

    await waitFor(() => expect(screen.getByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument());
    expect(window.location.pathname).toBe("/login");
  });

  it("rejects an expired persisted session", async () => {
    localStorage.setItem("conciliador.session", JSON.stringify({
      accessToken: "expired-token",
      user: validResponse.user,
      expiresAt: Date.now() - 1,
    }));
    renderApp("/");

    await waitFor(() => expect(screen.getByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument());
    expect(localStorage.getItem("conciliador.session")).toBeNull();
  });
});
