
import { useEffect, useState } from "react";
import { api } from "./api.js";
import "./styles.css";

function App() {
  const [page, setPage] = useState("home");
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [registerSchema, setRegisterSchema] = useState(null);
  const [formData, setFormData] = useState({});
  const [loginData, setLoginData] = useState({ email: "", password: "" });
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("bep_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    api
      .get("/health")
      .then((res) =>
        setApiStatus(res.data.status === "ok" ? "Online" : "Unavailable")
      )
      .catch(() => setApiStatus("Offline"));

    api
      .get("/openapi.json")
      .then((res) => {
        const spec = res.data;
        const requestSchema =
          spec.paths?.["/api/v1/auth/register"]?.post
            ?.requestBody?.content?.["application/json"]?.schema;

        let schema = requestSchema;

        if (schema?.$ref) {
          const name = schema.$ref.split("/").pop();
          schema = spec.components?.schemas?.[name];
        }

        if (schema?.properties) {
          setRegisterSchema({
            properties: schema.properties,
            required: schema.required || [],
          });
        }
      })
      .catch(() => {
        setMessage("Could not load registration fields. Check the backend.");
      });
  }, []);

  function navigate(nextPage) {
    setPage(nextPage);
    setMessage("");
    setMessageType("");
    setFormData({});
  }

  function getErrorMessage(error, fallback) {
    const data = error.response?.data;
    const detail = data?.error?.message ?? data?.detail;

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).join(", ");
    }

    return fallback;
  }

  async function handleRegister(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    setMessageType("");

    try {
      const response = await api.post("/api/v1/auth/register", formData);

      setMessage(
        `Registration successful! Welcome, ${response.data.name}. You can now sign in.`
      );
      setMessageType("success");
      setFormData({});
    } catch (error) {
      setMessage(
        getErrorMessage(error, "Registration failed. Please check your inputs.")
      );
      setMessageType("error");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    setMessageType("");

    try {
      const response = await api.post("/api/v1/auth/login", loginData);
      const { access_token, user: loggedInUser } = response.data;

      if (!access_token || !loggedInUser) {
        throw new Error("The server returned an incomplete login response.");
      }

      // Store the token and basic user details for subsequent frontend requests.
      localStorage.setItem("bep_token", access_token);
      localStorage.setItem("bep_user", JSON.stringify(loggedInUser));

      setUser(loggedInUser);
      setLoginData({ email: "", password: "" });
      setMessage(`Welcome back, ${loggedInUser.name}! You are signed in.`);
      setMessageType("success");
    } catch (error) {
      setMessage(
        error.response
          ? getErrorMessage(error, "Sign in failed. Please try again.")
          : error.message || "Could not connect to the login service."
      );
      setMessageType("error");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("bep_token");
    localStorage.removeItem("bep_user");
    setUser(null);
    setMessage("You have signed out.");
    setMessageType("success");
    setPage("home");
  }

  function renderRegisterField(name, definition) {
    const label = name
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

    const required = registerSchema.required.includes(name);
    const type =
      /password/i.test(name)
        ? "password"
        : /email/i.test(name)
          ? "email"
          : definition.type === "integer" || definition.type === "number"
            ? "number"
            : "text";

    return (
      <label className="field" key={name}>
        <span>
          {label}
          {required ? " *" : ""}
        </span>

        {definition.enum ? (
          <select
            value={formData[name] ?? ""}
            required={required}
            onChange={(event) =>
              setFormData({ ...formData, [name]: event.target.value })
            }
          >
            <option value="">Select {label.toLowerCase()}</option>
            {definition.enum.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        ) : (
          <input
            type={type}
            value={formData[name] ?? ""}
            required={required}
            minLength={definition.minLength}
            maxLength={definition.maxLength}
            placeholder={`Enter ${label.toLowerCase()}`}
            onChange={(event) =>
              setFormData({
                ...formData,
                [name]:
                  type === "number" && event.target.value !== ""
                    ? Number(event.target.value)
                    : event.target.value,
              })
            }
          />
        )}
      </label>
    );
  }

  return (
    <div className="app">
      <header className="navbar">
        <button className="brand" onClick={() => navigate("home")}>
          <span className="brand-icon">B</span>
          <span>
            Book<span className="brand-accent">Exchange</span>
          </span>
        </button>

        <nav className="nav-links" aria-label="Main navigation">
          <button onClick={() => navigate("home")}>Home</button>
          <button onClick={() => navigate("login")}>Browse Books</button>

          {user ? (
            <button className="nav-cta" onClick={handleLogout}>
              Sign out
            </button>
          ) : (
            <button
              className="nav-cta"
              onClick={() => navigate("register")}
            >
              Get Started
            </button>
          )}
        </nav>
      </header>

      <main>
        {page === "home" && (
          <section className="hero">
            <div className="hero-content">
              <span className="eyebrow">READ MORE. SHARE MORE.</span>
              <h1>
                Every book deserves <span>another chapter.</span>
              </h1>
              <p>
                Discover books, share stories, and connect with readers.
                Give your books a new home through our campus book exchange.
              </p>

              <div className="hero-actions">
                {user ? (
                  <button
                    className="primary-btn"
                    onClick={() => navigate("login")}
                  >
                    Continue exploring <span>→</span>
                  </button>
                ) : (
                  <>
                    <button
                      className="primary-btn"
                      onClick={() => navigate("register")}
                    >
                      Create an account <span>→</span>
                    </button>
                    <button
                      className="secondary-btn"
                      onClick={() => navigate("login")}
                    >
                      Sign in
                    </button>
                  </>
                )}
              </div>

              {user && (
                <p className="muted">
                  Signed in as <strong>{user.name}</strong>
                </p>
              )}

              <div className="status">
                <span
                  className={
                    apiStatus === "Online"
                      ? "status-dot"
                      : "status-dot offline"
                  }
                />
                API {apiStatus}
              </div>
            </div>

            <div className="book-art" aria-label="Book exchange illustration">
              <div className="book book-one">
                <span>SHARE</span>
                <strong>
                  Stories
                  <br />
                  that travel.
                </strong>
              </div>
              <div className="book book-two">
                <span>DISCOVER</span>
                <strong>
                  Your next
                  <br />
                  favourite.
                </strong>
              </div>
              <div className="book book-three">
                <span>REUSE</span>
                <strong>
                  Every book
                  <br />
                  matters.
                </strong>
              </div>
              <div className="art-circle">B</div>
            </div>
          </section>
        )}

        {page === "register" && (
          <section className="auth-layout">
            <div className="auth-intro">
              <span className="eyebrow">JOIN THE COMMUNITY</span>
              <h1>Your next chapter starts here.</h1>
              <p>
                Create an account to get started with the Book Exchange
                Platform.
              </p>
            </div>

            <div className="auth-card">
              <h2>Create account</h2>
              <p className="muted">Enter your details to register.</p>

              {registerSchema ? (
                <form onSubmit={handleRegister}>
                  {Object.entries(registerSchema.properties).map(
                    ([name, definition]) =>
                      renderRegisterField(name, definition)
                  )}

                  <button
                    className="primary-btn full-btn"
                    disabled={loading}
                  >
                    {loading ? "Creating account..." : "Create account"}
                  </button>
                </form>
              ) : (
                <p className="muted">
                  Loading registration fields from the backend...
                </p>
              )}

              {message && (
                <div
                  className="message"
                  role="status"
                  aria-live="polite"
                  data-type={messageType}
                >
                  {message}
                </div>
              )}

              <p className="auth-switch">
                Already registered?{" "}
                <button onClick={() => navigate("login")}>Sign in</button>
              </p>
            </div>
          </section>
        )}

        {page === "login" && (
          <section className="auth-layout">
            <div className="auth-intro">
              <span className="eyebrow">WELCOME BACK</span>
              <h1>Good books. Great connections.</h1>
              <p>Return to your book exchange community.</p>
            </div>

            <div className="auth-card">
              <h2>Sign in</h2>
              <p className="muted">
                Enter your registered email and password.
              </p>

              {user ? (
                <>
                  <p>
                    You are signed in as <strong>{user.name}</strong>.
                  </p>
                  <button
                    className="primary-btn full-btn"
                    onClick={() => navigate("home")}
                  >
                    Return home
                  </button>
                  <button
                    className="secondary-btn full-btn"
                    onClick={handleLogout}
                  >
                    Sign out
                  </button>
                </>
              ) : (
                <form onSubmit={handleLogin}>
                  <label className="field">
                    <span>Email</span>
                    <input
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      value={loginData.email}
                      required
                      onChange={(event) =>
                        setLoginData({
                          ...loginData,
                          email: event.target.value,
                        })
                      }
                    />
                  </label>

                  <label className="field">
                    <span>Password</span>
                    <input
                      type="password"
                      autoComplete="current-password"
                      placeholder="Enter your password"
                      value={loginData.password}
                      required
                      onChange={(event) =>
                        setLoginData({
                          ...loginData,
                          password: event.target.value,
                        })
                      }
                    />
                  </label>

                  <button
                    className="primary-btn full-btn"
                    disabled={loading}
                  >
                    {loading ? "Signing in..." : "Sign in"}
                  </button>
                </form>
              )}

              {message && (
                <div
                  className="message"
                  role="status"
                  aria-live="polite"
                  data-type={messageType}
                >
                  {message}
                </div>
              )}

              {!user && (
                <p className="auth-switch">
                  New here?{" "}
                  <button onClick={() => navigate("register")}>
                    Create an account
                  </button>
                </p>
              )}
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <span>BookExchange</span>
        <span>Built for readers, by readers.</span>
        <span>API: {apiStatus}</span>
      </footer>
    </div>
  );
}

export default App;
