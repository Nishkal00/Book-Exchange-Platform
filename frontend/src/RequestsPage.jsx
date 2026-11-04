import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

// BEP-39: request a book, see matches, accept or decline.
// Uses /api/v1/requests and /api/v1/matches. No partner contact details are shown here;
// they are disclosed only after mutual acceptance (SR-007).

function authConfig() {
  return {
    headers: { Authorization: `Bearer ${localStorage.getItem("bep_token")}` },
  };
}

export function errorText(error, fallback = "Something went wrong. Please try again.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") {
    return detail.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg?.replace(/^Value error, /, "")).filter(Boolean).join(" ");
  }
  if (error?.response?.data?.error?.message) return error.response.data.error.message;
  if (!error?.response) return "Cannot reach the server. Check your connection and try again.";
  return fallback;
}

const REQUEST_STATUS_TEXT = {
  OPEN: "Open: waiting for a match",
  MATCHED: "Matched",
  FULFILLED: "Fulfilled: exchange created",
  CANCELLED: "Cancelled",
};

function matchStatusText(match) {
  if (match.status === "ACCEPTED") {
    return match.exchange_id
      ? `Both accepted. Exchange #${match.exchange_id} created.`
      : "Both accepted.";
  }
  if (match.status === "DECLINED") return "Declined";
  if (match.my_decision && !match.partner_decision) return "You accepted. Waiting for the other person.";
  if (!match.my_decision && match.partner_decision) return "The other person accepted. Your decision is needed.";
  return "Waiting for decisions";
}

function RequestsPage({ user, prefill, onPrefillUsed }) {
  const [mode, setMode] = useState("isbn");
  const [isbn, setIsbn] = useState("");
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState(user?.location || "");
  const [submitting, setSubmitting] = useState(false);

  const [requests, setRequests] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [notice, setNotice] = useState({ text: "", type: "" });

  useEffect(() => {
    if (!prefill) return;
    setMode("isbn");
    setIsbn(prefill.isbn || "");
    if (prefill.location) setLocation(prefill.location);
    setNotice({ text: `Ready to request "${prefill.title}". Check the location and submit.`, type: "success" });
    onPrefillUsed?.();
  }, [prefill, onPrefillUsed]);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [reqRes, matchRes] = await Promise.all([
        api.get("/api/v1/requests", authConfig()),
        api.get("/api/v1/matches", authConfig()),
      ]);
      setRequests(reqRes.data);
      setMatches(matchRes.data);
    } catch (error) {
      setLoadError(errorText(error, "Could not load your requests."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmit(event) {
    event.preventDefault();
    setNotice({ text: "", type: "" });
    const payload = { location: location.trim() };
    if (mode === "isbn") payload.isbn = isbn.trim();
    else payload.title_query = title.trim();

    setSubmitting(true);
    try {
      await api.post("/api/v1/requests", payload, authConfig());
      setNotice({ text: "Request created. Use Find matches to look for available books.", type: "success" });
      setIsbn("");
      setTitle("");
      await load();
    } catch (error) {
      setNotice({ text: errorText(error), type: "error" });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel(request) {
    setBusyId(`r${request.id}`);
    setNotice({ text: "", type: "" });
    try {
      await api.post(`/api/v1/requests/${request.id}/cancel`, null, authConfig());
      setNotice({ text: "Request cancelled.", type: "success" });
      await load();
    } catch (error) {
      setNotice({ text: errorText(error), type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  async function handleFindMatches(request) {
    setBusyId(`r${request.id}`);
    setNotice({ text: "", type: "" });
    try {
      const res = await api.get(`/api/v1/requests/${request.id}/matches`, authConfig());
      setNotice({
        text: res.data.length
          ? `Found ${res.data.length} possible match${res.data.length === 1 ? "" : "es"}. Review them below.`
          : "No available book matches this request yet. Try again later.",
        type: res.data.length ? "success" : "error",
      });
      await load();
    } catch (error) {
      setNotice({ text: errorText(error), type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  async function handleDecision(match, decision) {
    setBusyId(`m${match.match_id}`);
    setNotice({ text: "", type: "" });
    try {
      const res = await api.post(
        `/api/v1/matches/${match.match_id}/decision`,
        { decision },
        authConfig()
      );
      let text = decision === "accept" ? "You accepted this match." : "You declined this match.";
      if (res.data.exchangeId) text = `Both of you accepted. Exchange #${res.data.exchangeId} was created.`;
      setNotice({ text, type: "success" });
      await load();
    } catch (error) {
      setNotice({ text: errorText(error), type: "error" });
      await load();
    } finally {
      setBusyId(null);
    }
  }

  const canCancel = (request) => request.status === "OPEN" || request.status === "MATCHED";

  return (
    <section className="browse-page requests-page">
      <div className="browse-heading">
        <span className="eyebrow">BORROW AND LEND</span>
        <h1>Requests and Matches</h1>
        <p>Ask for a book, then accept or decline the matches we find for you.</p>
      </div>

      <form className="profile-form-panel" onSubmit={handleSubmit}>
        <div className="form-panel-heading">
          <h2>Request a book</h2>
        </div>

        <div className="request-mode" role="group" aria-label="Request by">
          <button type="button" className={mode === "isbn" ? "primary-btn" : "secondary-btn"} onClick={() => setMode("isbn")}>
            By ISBN
          </button>
          <button type="button" className={mode === "title" ? "primary-btn" : "secondary-btn"} onClick={() => setMode("title")}>
            By title
          </button>
        </div>

        <div className="listing-form-grid">
          {mode === "isbn" ? (
            <label className="field">
              <span>ISBN (10 or 13 digits) *</span>
              <input required value={isbn} maxLength={17} placeholder="9780131103627" onChange={(e) => setIsbn(e.target.value)} />
            </label>
          ) : (
            <label className="field">
              <span>Book title or author *</span>
              <input required value={title} maxLength={200} placeholder="Introduction to Algorithms" onChange={(e) => setTitle(e.target.value)} />
            </label>
          )}
          <label className="field">
            <span>Your location *</span>
            <input required value={location} maxLength={100} placeholder="Campus library" onChange={(e) => setLocation(e.target.value)} />
          </label>
        </div>

        <button className="primary-btn" type="submit" disabled={submitting}>
          {submitting ? "Sending..." : "Send request"}
        </button>
      </form>

      {notice.text && (
        <div className="message" role="status" data-type={notice.type}>{notice.text}</div>
      )}

      {loading ? (
        <div className="listing-state"><div className="loader" /><p>Loading...</p></div>
      ) : loadError ? (
        <div className="listing-state error-state">
          <h3>Could not load</h3>
          <p>{loadError}</p>
          <button className="primary-btn" type="button" onClick={load}>Try Again</button>
        </div>
      ) : (
        <>
          <div className="requests-block">
            <h2>My requests</h2>
            {requests.length === 0 ? (
              <p className="requests-empty">You have no requests yet. Use the form above, or press Request this book on the Browse page.</p>
            ) : (
              <ul className="request-list">
                {requests.map((request) => (
                  <li className="request-row" key={request.id}>
                    <div>
                      <strong>{request.isbn ? `ISBN ${request.isbn}` : request.query}</strong>
                      <span>{request.location} · {REQUEST_STATUS_TEXT[request.status] || request.status}</span>
                    </div>
                    <div className="listing-card-actions">
                      {(request.status === "OPEN" || request.status === "MATCHED") && (
                        <button className="secondary-btn" type="button" disabled={busyId === `r${request.id}`} onClick={() => handleFindMatches(request)}>
                          Find matches
                        </button>
                      )}
                      {canCancel(request) && (
                        <button className="danger-btn" type="button" disabled={busyId === `r${request.id}`} onClick={() => handleCancel(request)}>
                          Cancel
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="requests-block">
            <h2>Matches</h2>
            {matches.length === 0 ? (
              <p className="requests-empty">No matches yet. Press Find matches on a request, or wait until someone lists a matching book.</p>
            ) : (
              <ul className="request-list">
                {matches.map((match) => {
                  const open = match.status === "PROPOSED";
                  const needsMe = open && !match.my_decision;
                  return (
                    <li className="request-row" key={match.match_id}>
                      <div>
                        <strong>{match.title}</strong>
                        <span>
                          by {match.author} · {match.location} · You are the {match.role}
                        </span>
                        <span className="match-state">{matchStatusText(match)}</span>
                      </div>
                      {needsMe && (
                        <div className="listing-card-actions">
                          <button className="primary-btn" type="button" disabled={busyId === `m${match.match_id}`} onClick={() => handleDecision(match, "accept")}>
                            Accept
                          </button>
                          <button className="danger-btn" type="button" disabled={busyId === `m${match.match_id}`} onClick={() => handleDecision(match, "decline")}>
                            Decline
                          </button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export default RequestsPage;
