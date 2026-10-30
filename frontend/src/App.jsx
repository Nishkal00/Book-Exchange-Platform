
import { useEffect, useState } from "react";
import { api } from "./api.js";
import "./styles.css";

const PAGE_SIZE = 20;

const EMPTY_FILTERS = {
  q: "",
  isbn: "",
  location: "",
};

function App() {
  const [page, setPage] = useState("home");
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [registerSchema, setRegisterSchema] = useState(null);

  const [formData, setFormData] = useState({});
  const [loginData, setLoginData] = useState({
    email: "",
    password: "",
  });

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");
  const [loading, setLoading] = useState(false);

  // Restore only a valid locally stored session.
  const [user, setUser] = useState(() => {
    try {
      const token = localStorage.getItem("bep_token");
      const saved = localStorage.getItem("bep_user");

      if (!token || !saved) {
        localStorage.removeItem("bep_token");
        localStorage.removeItem("bep_user");
        return null;
      }

      return JSON.parse(saved);
    } catch {
      localStorage.removeItem("bep_token");
      localStorage.removeItem("bep_user");
      return null;
    }
  });

  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);

  const [listings, setListings] = useState([]);
  const [listingLoading, setListingLoading] = useState(false);
  const [listingError, setListingError] = useState("");

  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // --------------------------------------------------
  // API health and registration schema
  // --------------------------------------------------

  useEffect(() => {
    api
      .get("/health")
      .then((response) => {
        setApiStatus(
          response.data.status === "ok" ? "Online" : "Unavailable"
        );
      })
      .catch(() => {
        setApiStatus("Offline");
      });

    api
      .get("/openapi.json")
      .then((response) => {
        const spec = response.data;

        let schema =
          spec.paths?.["/api/v1/auth/register"]?.post?.requestBody
            ?.content?.["application/json"]?.schema;

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
        setMessage(
          "Could not load registration fields. Check the backend."
        );
        setMessageType("error");
      });
  }, []);

  // --------------------------------------------------
  // Error handling
  // --------------------------------------------------

  function getErrorMessage(error, fallback) {
    const data = error.response?.data;
    const detail = data?.error?.message ?? data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).join(", ");
    }

    return fallback;
  }

  // --------------------------------------------------
  // Fetch listings
  // --------------------------------------------------

  async function fetchListings(
    endpoint,
    authenticated = false,
    pageNumber = currentPage,
    searchFilters = appliedFilters
  ) {
    setListingLoading(true);
    setListingError("");

    try {
      const token = localStorage.getItem("bep_token");

      // Do not send an authenticated request without a token.
      if (authenticated && !token) {
        setListings([]);
        setTotal(0);
        setListingError(
          "Your session has expired. Please sign in again."
        );

        localStorage.removeItem("bep_token");
        localStorage.removeItem("bep_user");
        setUser(null);

        return;
      }

      const response = await api.get(endpoint, {
        params: {
          ...(authenticated ? {} : searchFilters),
          page: pageNumber,
          size: PAGE_SIZE,
        },
        ...(authenticated
          ? {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            }
          : {}),
      });

      setListings(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      setListings([]);
      setTotal(0);

      if (error.response?.status === 401 && authenticated) {
        localStorage.removeItem("bep_token");
        localStorage.removeItem("bep_user");
        setUser(null);

        setListingError(
          "Your session has expired. Please sign in again."
        );
      } else {
        setListingError(
          getErrorMessage(
            error,
            "Could not load books. Please try again."
          )
        );
      }
    } finally {
      setListingLoading(false);
    }
  }

  // --------------------------------------------------
  // Load results when navigation, pagination or
  // submitted search filters change.
  // --------------------------------------------------

  useEffect(() => {
    if (page === "browse") {
      fetchListings(
        "/api/v1/listings",
        false,
        currentPage,
        appliedFilters
      );
    } else if (page === "mine" && user) {
      fetchListings(
        "/api/v1/listings/mine",
        true,
        currentPage
      );
    }

    // Filters are applied only when the search form is submitted.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, currentPage, user, appliedFilters]);

  // --------------------------------------------------
  // Navigation
  // --------------------------------------------------

  function navigate(nextPage) {
    if (nextPage === "mine" && !user) {
      setPage("login");
      setMessage("Please sign in to view your listings.");
      setMessageType("error");
      return;
    }

    setPage(nextPage);
    setMessage("");
    setMessageType("");
    setListingError("");

    if (nextPage === "browse" || nextPage === "mine") {
      setCurrentPage(1);
    }
  }

  // --------------------------------------------------
  // Search and clear filters
  // --------------------------------------------------

  function handleSearch(event) {
    event.preventDefault();

    setCurrentPage(1);
    setAppliedFilters({ ...filters });
  }

  function handleClearFilters() {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setCurrentPage(1);
  }

  // --------------------------------------------------
  // Registration
  // --------------------------------------------------

  async function handleRegister(event) {
    event.preventDefault();

    setLoading(true);
    setMessage("");
    setMessageType("");

    try {
      const response = await api.post(
        "/api/v1/auth/register",
        formData
      );

      setMessage(
        `Registration successful! Welcome, ${response.data.name}. You can now sign in.`
      );
      setMessageType("success");
      setFormData({});
    } catch (error) {
      setMessage(
        getErrorMessage(
          error,
          "Registration failed. Please check your inputs."
        )
      );
      setMessageType("error");
    } finally {
      setLoading(false);
    }
  }

  // --------------------------------------------------
  // Login
  // --------------------------------------------------

  async function handleLogin(event) {
    event.preventDefault();

    setLoading(true);
    setMessage("");
    setMessageType("");

    try {
      const response = await api.post(
        "/api/v1/auth/login",
        loginData
      );

      const { access_token, user: loggedInUser } = response.data;

      if (!access_token || !loggedInUser) {
        throw new Error(
          "The server returned an incomplete login response."
        );
      }

      localStorage.setItem("bep_token", access_token);
      localStorage.setItem(
        "bep_user",
        JSON.stringify(loggedInUser)
      );

      setUser(loggedInUser);
      setLoginData({
        email: "",
        password: "",
      });

      setMessage(`Welcome back, ${loggedInUser.name}!`);
      setMessageType("success");

      // Move to Browse after successful authentication.
      setPage("browse");
      setCurrentPage(1);
      setListingError("");
    } catch (error) {
      setMessage(
        error.response
          ? getErrorMessage(
              error,
              "Sign in failed. Please try again."
            )
          : error.message ||
              "Could not connect to the login service."
      );

      setMessageType("error");
    } finally {
      setLoading(false);
    }
  }

  // --------------------------------------------------
  // Logout
  // --------------------------------------------------

  function handleLogout() {
    localStorage.removeItem("bep_token");
    localStorage.removeItem("bep_user");

    setUser(null);
    setListings([]);
    setTotal(0);

    setMessage("You have signed out.");
    setMessageType("success");
    setListingError("");

    setPage("home");
  }

  // --------------------------------------------------
  // Dynamic registration fields
  // --------------------------------------------------

  function renderRegisterField(name, definition) {
    const label = name
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

    const required = registerSchema.required.includes(name);

    const type = /password/i.test(name)
      ? "password"
      : /email/i.test(name)
        ? "email"
        : definition.type === "integer" ||
            definition.type === "number"
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
              setFormData({
                ...formData,
                [name]: event.target.value,
              })
            }
          >
            <option value="">
              Select {label.toLowerCase()}
            </option>

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
                [name]: event.target.value,
              })
            }
          />
        )}
      </label>
    );
  }

  // --------------------------------------------------
  // Browse and My Listings
  // --------------------------------------------------

  function renderListings() {
    const isMine = page === "mine";

    return (
      <section className="browse-page">
        <div className="browse-heading">
          <span className="eyebrow">
            {isMine
              ? "YOUR COLLECTION"
              : "EXPLORE THE COLLECTION"}
          </span>

          <h1>{isMine ? "My Listings" : "Browse Books"}</h1>

          <p>
            {isMine
              ? "View the books you have listed on BookExchange."
              : "Find your next favourite book from the campus community."}
          </p>
        </div>

        {!isMine && (
          <form className="search-panel" onSubmit={handleSearch}>
            <label className="field">
              <span>Title or Author</span>

              <input
                type="search"
                placeholder="Search by book title or author..."
                value={filters.q}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    q: event.target.value,
                  })
                }
              />
            </label>

            <label className="field">
              <span>ISBN</span>

              <input
                type="search"
                placeholder="Enter ISBN"
                value={filters.isbn}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    isbn: event.target.value,
                  })
                }
              />
            </label>

            <label className="field">
              <span>Location</span>

              <input
                type="search"
                placeholder="Enter location"
                value={filters.location}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    location: event.target.value,
                  })
                }
              />
            </label>

            <div className="search-actions">
              <button className="primary-btn" type="submit">
                Search Books
              </button>

              <button
                className="secondary-btn"
                type="button"
                onClick={handleClearFilters}
              >
                Clear Filters
              </button>
            </div>
          </form>
        )}

        <div className="results-heading">
          <div>
            <span className="eyebrow">
              BOOK EXCHANGE COLLECTION
            </span>

            <h2>{isMine ? "Your Books" : "Available Books"}</h2>
          </div>

          <span>
            {total} {total === 1 ? "book" : "books"} found
          </span>
        </div>

        {listingLoading ? (
          <div className="listing-state">
            <div className="loader" />
            <p>Finding books for you...</p>
          </div>
        ) : listingError ? (
          <div className="listing-state error-state" role="alert">
            <h3>Unable to load books</h3>
            <p>{listingError}</p>

            {listingError.includes("sign in") && (
              <button
                className="secondary-btn"
                onClick={() => navigate("login")}
              >
                Sign in
              </button>
            )}

            <button
              className="primary-btn"
              onClick={() =>
                fetchListings(
                  isMine
                    ? "/api/v1/listings/mine"
                    : "/api/v1/listings",
                  isMine,
                  currentPage,
                  appliedFilters
                )
              }
            >
              Try Again
            </button>
          </div>
        ) : listings.length === 0 ? (
          <div className="listing-state">
            <div className="empty-book">B</div>

            <h3>No books found</h3>

            <p>
              {isMine
                ? "You have not listed any books yet."
                : "Try changing your search terms or clearing the filters."}
            </p>

            {!isMine && (
              <button
                className="secondary-btn"
                onClick={handleClearFilters}
              >
                View All Books
              </button>
            )}
          </div>
        ) : (
          <div className="listing-grid">
            {listings.map((book) => (
              <article className="listing-card" key={book.id}>
                <div className="listing-cover">
                  <span>BOOK EXCHANGE</span>

                  <strong>
                    {book.title?.charAt(0)?.toUpperCase() || "B"}
                  </strong>

                  <small>{book.condition} CONDITION</small>
                </div>

                <div className="listing-info">
                  <span className="listing-status">
                    {book.status}
                  </span>

                  <h3>{book.title}</h3>

                  <p className="listing-author">
                    by {book.author}
                  </p>

                  <div className="listing-details">
                    <p>
                      <strong>ISBN:</strong> {book.isbn}
                    </p>

                    <p>
                      <strong>Condition:</strong> {book.condition}
                    </p>

                    <p>
                      <strong>Location:</strong> {book.location}
                    </p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        {!listingLoading && !listingError && total > 0 && (
          <div className="pagination">
            <button
              className="secondary-btn"
              disabled={currentPage <= 1}
              onClick={() =>
                setCurrentPage((value) => value - 1)
              }
            >
              ← Previous
            </button>

            <span>
              Page {currentPage} of {totalPages}
            </span>

            <button
              className="secondary-btn"
              disabled={currentPage >= totalPages}
              onClick={() =>
                setCurrentPage((value) => value + 1)
              }
            >
              Next →
            </button>
          </div>
        )}
      </section>
    );
  }

  // --------------------------------------------------
  // Main UI
  // --------------------------------------------------

  return (
    <div className="app">
      <header className="navbar">
        <button
          className="brand"
          onClick={() => navigate("home")}
        >
          <span className="brand-icon">B</span>

          <span>
            Book<span className="brand-accent">Exchange</span>
          </span>
        </button>

        <nav className="nav-links" aria-label="Main navigation">
          <button
            className={page === "home" ? "active" : ""}
            onClick={() => navigate("home")}
          >
            Home
          </button>

          <button
            className={page === "browse" ? "active" : ""}
            onClick={() => navigate("browse")}
          >
            Browse Books
          </button>

          {user && (
            <button
              className={page === "mine" ? "active" : ""}
              onClick={() => navigate("mine")}
            >
              My Listings
            </button>
          )}

          {user ? (
            <button className="nav-cta" onClick={handleLogout}>
              Sign out
            </button>
          ) : (
            <>
              <button onClick={() => navigate("login")}>
                Sign in
              </button>

              <button
                className="nav-cta"
                onClick={() => navigate("register")}
              >
                Get Started
              </button>
            </>
          )}
        </nav>
      </header>

      <main>
        {/* HOME */}

        {page === "home" && (
          <section className="hero">
            <div className="hero-content">
              <span className="eyebrow">
                READ MORE. SHARE MORE.
              </span>

              <h1>
                Every book deserves{" "}
                <span>another chapter.</span>
              </h1>

              <p>
                Discover books, share stories, and connect with readers.
                Give your books a new home through our campus book exchange.
              </p>

              <div className="hero-actions">
                <button
                  className="primary-btn"
                  onClick={() => navigate("browse")}
                >
                  Browse books →
                </button>

                {!user && (
                  <button
                    className="secondary-btn"
                    onClick={() => navigate("register")}
                  >
                    Create an account
                  </button>
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

            <div
              className="book-art"
              aria-label="Book exchange illustration"
            >
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

        {/* BROWSE AND MY LISTINGS */}

        {(page === "browse" || page === "mine") &&
          renderListings()}

        {/* REGISTER */}

        {page === "register" && (
          <section className="auth-layout">
            <div className="auth-intro">
              <span className="eyebrow">JOIN THE COMMUNITY</span>

              <h1>Your next chapter starts here.</h1>

              <p>
                Create an account to get started with the Book Exchange
                Platform.
              </p>

              <div className="auth-decoration">
                <div className="decoration-book">B</div>
                <span>READ. SHARE. REPEAT.</span>
              </div>
            </div>

            <div className="auth-card">
              <span className="eyebrow">BOOK EXCHANGE</span>

              <h2>Create account</h2>

              <p className="muted">
                Enter your details to register.
              </p>

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
                    {loading
                      ? "Creating account..."
                      : "Create account"}
                  </button>
                </form>
              ) : (
                <p className="muted">
                  Loading registration fields...
                </p>
              )}

              {message && (
                <div
                  className="message"
                  role="status"
                  data-type={messageType}
                >
                  {message}
                </div>
              )}

              <p className="auth-switch">
                Already registered?{" "}
                <button onClick={() => navigate("login")}>
                  Sign in
                </button>
              </p>
            </div>
          </section>
        )}

        {/* LOGIN */}

        {page === "login" && (
          <section className="auth-layout">
            <div className="auth-intro">
              <span className="eyebrow">WELCOME BACK</span>

              <h1>Good books. Great connections.</h1>

              <p>
                Return to your book exchange community.
              </p>

              <div className="auth-decoration">
                <div className="decoration-book">B</div>
                <span>YOUR NEXT CHAPTER AWAITS.</span>
              </div>
            </div>

            <div className="auth-card">
              <span className="eyebrow">BOOK EXCHANGE</span>

              <h2>Sign in</h2>

              <p className="muted">
                Enter your registered email and password.
              </p>

              {user ? (
                <>
                  <p>
                    You are signed in as{" "}
                    <strong>{user.name}</strong>.
                  </p>

                  <button
                    className="primary-btn full-btn"
                    onClick={() => navigate("browse")}
                  >
                    Browse books
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
        <div className="footer-brand">
          <span className="brand-icon">B</span>
          <strong>BookExchange</strong>
        </div>

        <span>Built for readers, by readers.</span>

        <span className="footer-status">
          <span
            className={
              apiStatus === "Online"
                ? "status-dot"
                : "status-dot offline"
            }
          />
          API: {apiStatus}
        </span>
      </footer>
    </div>
  );
}

export default App;
