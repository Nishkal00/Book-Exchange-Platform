
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

  // My Listings and Profile
  const EMPTY_LISTING_FORM = {
    title: "",
    author: "",
    isbn: "",
    condition: "GOOD",
    location: "",
  };
  const [showListingForm, setShowListingForm] = useState(false);
  const [editingListing, setEditingListing] = useState(null);
  const [listingForm, setListingForm] = useState(EMPTY_LISTING_FORM);
  const [listingSaving, setListingSaving] = useState(false);
  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState({
    name: "",
    department: "",
    location: "",
  });
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);

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
    else if (page === "profile" && user) {
      fetchProfile();
    }

    // Filters are applied only when the search form is submitted.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, currentPage, user, appliedFilters]);

  // --------------------------------------------------
  // Navigation
  // --------------------------------------------------

  function navigate(nextPage) {
    if ((nextPage === "mine" || nextPage === "profile") && !user) {
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
  // My Listings actions
  // --------------------------------------------------

  function authConfig() {
    return {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("bep_token")}`,
      },
    };
  }

  function openCreateListing() {
    setEditingListing(null);
    setListingForm(EMPTY_LISTING_FORM);
    setShowListingForm(true);
    setMessage("");
    setMessageType("");
  }

  function openEditListing(book) {
    setEditingListing(book);
    setListingForm({
      title: book.title || "",
      author: book.author || "",
      isbn: book.isbn || "",
      condition: book.condition || "GOOD",
      location: book.location || "",
    });
    setShowListingForm(true);
    setMessage("");
    setMessageType("");
  }

  function closeListingForm() {
    setShowListingForm(false);
    setEditingListing(null);
    setListingForm(EMPTY_LISTING_FORM);
  }

  async function handleListingSubmit(event) {
    event.preventDefault();
    setListingSaving(true);
    setMessage("");
    setMessageType("");

    const payload = {
      title: listingForm.title.trim(),
      author: listingForm.author.trim(),
      isbn: listingForm.isbn.replace(/-/g, "").trim(),
      condition: listingForm.condition,
      location: listingForm.location.trim(),
    };

    try {
      if (editingListing) {
        await api.patch(
          `/api/v1/listings/${editingListing.id}`,
          payload,
          authConfig()
        );
        setMessage("Listing updated successfully.");
      } else {
        await api.post("/api/v1/listings", payload, authConfig());
        setMessage("Book listed successfully.");
      }

      setMessageType("success");
      closeListingForm();
      setCurrentPage(1);
      await fetchListings("/api/v1/listings/mine", true, 1);
    } catch (error) {
      setMessage(getErrorMessage(error, "Could not save the listing."));
      setMessageType("error");
    } finally {
      setListingSaving(false);
    }
  }

  async function handleListingStatusChange(book) {
    const nextStatus =
      book.status === "AVAILABLE" ? "UNAVAILABLE" : "AVAILABLE";

    try {
      await api.patch(
        `/api/v1/listings/${book.id}`,
        { status: nextStatus },
        authConfig()
      );
      setMessage(`Listing marked ${nextStatus.toLowerCase()}.`);
      setMessageType("success");
      await fetchListings("/api/v1/listings/mine", true, currentPage);
    } catch (error) {
      setMessage(getErrorMessage(error, "Could not update listing status."));
      setMessageType("error");
    }
  }

  async function handleDeleteListing(book) {
    if (!window.confirm(`Delete "${book.title}"?`)) return;

    try {
      await api.delete(`/api/v1/listings/${book.id}`, authConfig());
      setMessage("Listing deleted successfully.");
      setMessageType("success");
      await fetchListings("/api/v1/listings/mine", true, currentPage);
    } catch (error) {
      setMessage(getErrorMessage(error, "Could not delete this listing."));
      setMessageType("error");
    }
  }

  // --------------------------------------------------
  // Profile
  // --------------------------------------------------

  async function fetchProfile() {
    setProfileLoading(true);
    setMessage("");
    setMessageType("");

    try {
      const response = await api.get("/api/v1/auth/me", authConfig());
      setProfile(response.data);
      setProfileForm({
        name: response.data.name || "",
        department: response.data.department || "",
        location: response.data.location || "",
      });
    } catch (error) {
      setMessage(getErrorMessage(error, "Could not load your profile."));
      setMessageType("error");
    } finally {
      setProfileLoading(false);
    }
  }

  async function handleProfileSubmit(event) {
    event.preventDefault();
    setProfileSaving(true);
    setMessage("");
    setMessageType("");

    try {
      const payload = {
        name: profileForm.name.trim(),
        department: profileForm.department.trim() || null,
        location: profileForm.location.trim(),
      };
      const response = await api.patch(
        "/api/v1/auth/me",
        payload,
        authConfig()
      );

      setProfile(response.data);
      setProfileForm({
        name: response.data.name || "",
        department: response.data.department || "",
        location: response.data.location || "",
      });

      const updatedUser = { ...user, ...response.data };
      setUser(updatedUser);
      localStorage.setItem("bep_user", JSON.stringify(updatedUser));

      setMessage("Profile updated successfully.");
      setMessageType("success");
    } catch (error) {
      setMessage(getErrorMessage(error, "Could not update your profile."));
      setMessageType("error");
    } finally {
      setProfileSaving(false);
    }
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
            <span className="eyebrow">BOOK EXCHANGE COLLECTION</span>
            <h2>{isMine ? "Your Books" : "Available Books"}</h2>
          </div>
          <div className="results-actions">
            <span>{total} {total === 1 ? "book" : "books"} found</span>
            {isMine && (
              <button className="primary-btn" type="button" onClick={openCreateListing}>
                + Add a Book
              </button>
            )}
          </div>
        </div>

        {isMine && message && (
          <div className="message" role="status" data-type={messageType}>
            {message}
          </div>
        )}

        {isMine && showListingForm && (
          <form className="listing-form-panel" onSubmit={handleListingSubmit}>
            <div className="form-panel-heading">
              <div>
                <span className="eyebrow">{editingListing ? "UPDATE YOUR BOOK" : "SHARE A BOOK"}</span>
                <h2>{editingListing ? "Edit Listing" : "Create Listing"}</h2>
              </div>
              <button type="button" className="form-close-btn" onClick={closeListingForm} aria-label="Close form">×</button>
            </div>

            <div className="listing-form-grid">
              <label className="field">
                <span>Book Title *</span>
                <input required maxLength={200} value={listingForm.title}
                  onChange={(e) => setListingForm({ ...listingForm, title: e.target.value })}
                  placeholder="Enter book title" />
              </label>
              <label className="field">
                <span>Author *</span>
                <input required maxLength={150} value={listingForm.author}
                  onChange={(e) => setListingForm({ ...listingForm, author: e.target.value })}
                  placeholder="Enter author name" />
              </label>
              <label className="field">
                <span>ISBN *</span>
                <input required value={listingForm.isbn}
                  onChange={(e) => setListingForm({ ...listingForm, isbn: e.target.value })}
                  placeholder="10 or 13 digit ISBN" />
              </label>
              <label className="field">
                <span>Condition *</span>
                <select required value={listingForm.condition}
                  onChange={(e) => setListingForm({ ...listingForm, condition: e.target.value })}>
                  <option value="NEW">New</option>
                  <option value="GOOD">Good</option>
                  <option value="FAIR">Fair</option>
                  <option value="POOR">Poor</option>
                </select>
              </label>
              <label className="field">
                <span>Location *</span>
                <input required maxLength={100} value={listingForm.location}
                  onChange={(e) => setListingForm({ ...listingForm, location: e.target.value })}
                  placeholder="Enter pickup location" />
              </label>
            </div>
            <div className="listing-form-actions">
              <button className="primary-btn" type="submit" disabled={listingSaving}>
                {listingSaving ? "Saving..." : editingListing ? "Save Changes" : "Create Listing"}
              </button>
              <button className="secondary-btn" type="button" onClick={closeListingForm} disabled={listingSaving}>
                Cancel
              </button>
            </div>
          </form>
        )}

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

                  {isMine && (
                    <div className="listing-card-actions">
                      <button className="secondary-btn" type="button" onClick={() => openEditListing(book)}>
                        Edit
                      </button>
                      <button
                        className="secondary-btn"
                        type="button"
                        onClick={() => handleListingStatusChange(book)}
                        disabled={book.status === "RESERVED" || book.status === "ON_LOAN"}
                      >
                        {book.status === "AVAILABLE" ? "Mark Unavailable" : "Mark Available"}
                      </button>
                      <button className="danger-btn" type="button" onClick={() => handleDeleteListing(book)}>
                        Delete
                      </button>
                    </div>
                  )}
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
          {user && (
            <button
              className={page === "profile" ? "active" : ""}
              onClick={() => navigate("profile")}
            >
              Profile
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

        {/* PROFILE */}

        {page === "profile" && user && (
          <section className="browse-page profile-page">
            <div className="browse-heading">
              <span className="eyebrow">YOUR ACCOUNT</span>
              <h1>Profile</h1>
              <p>Manage your personal information and campus details.</p>
            </div>

            {profileLoading ? (
              <div className="listing-state"><div className="loader" /><p>Loading profile...</p></div>
            ) : profile ? (
              <form className="profile-form-panel" onSubmit={handleProfileSubmit}>
                <div className="profile-readonly-grid">
                  <div className="profile-readonly">
                    <span>Email address</span>
                    <strong>{profile.email}</strong>
                  </div>
                  <div className="profile-readonly">
                    <span>Account role</span>
                    <strong>{profile.role}</strong>
                  </div>
                </div>

                <div className="listing-form-grid">
                  <label className="field">
                    <span>Full name *</span>
                    <input required maxLength={100} value={profileForm.name}
                      onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })} />
                  </label>
                  <label className="field">
                    <span>Department</span>
                    <input maxLength={100} value={profileForm.department}
                      onChange={(e) => setProfileForm({ ...profileForm, department: e.target.value })} />
                  </label>
                  <label className="field">
                    <span>Location *</span>
                    <input required maxLength={100} value={profileForm.location}
                      onChange={(e) => setProfileForm({ ...profileForm, location: e.target.value })} />
                  </label>
                </div>

                <button className="primary-btn" type="submit" disabled={profileSaving}>
                  {profileSaving ? "Saving..." : "Save Profile"}
                </button>
              </form>
            ) : (
              <div className="listing-state error-state">
                <h3>Profile unavailable</h3>
                <p>{message || "Could not load your profile."}</p>
                <button className="primary-btn" type="button" onClick={fetchProfile}>Try Again</button>
              </div>
            )}

            {message && (
              <div className="message" role="status" data-type={messageType}>{message}</div>
            )}
          </section>
        )}

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
