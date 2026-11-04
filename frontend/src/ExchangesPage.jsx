import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { errorText } from "./RequestsPage.jsx";

function authConfig() {
  return {
    headers: { Authorization: `Bearer ${localStorage.getItem("bep_token")}` },
  };
}

const STATE_LABELS = {
  ACCEPTED: { label: "Accepted (Pending Handover)", className: "status-accepted" },
  ON_LOAN: { label: "On Loan", className: "status-on-loan" },
  RETURNED: { label: "Returned", className: "status-returned" },
  CANCELLED: { label: "Cancelled", className: "status-cancelled" },
};

function formatDate(dateStr) {
  if (!dateStr) return "Not set";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

function getTomorrowMinDate() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow.toISOString().split("T")[0];
}

function ExchangesPage({ user, initialExchangeId, onClearInitialExchange, onNavigate }) {
  const [exchanges, setExchanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [tabFilter, setTabFilter] = useState("ALL"); // ALL, ACTIVE, RETURNED, CANCELLED

  // Detail view state
  const [selectedExchange, setSelectedExchange] = useState(null);
  const [exchangeDetail, setExchangeDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  // Contact state
  const [contact, setContact] = useState(null);
  const [contactLoading, setContactLoading] = useState(false);
  const [contactNotice, setContactNotice] = useState("");

  // Due date form state
  const [dueDateInput, setDueDateInput] = useState("");
  const [dueDateSaving, setDueDateSaving] = useState(false);

  // Handover / Cancel actions state
  const [actionBusy, setActionBusy] = useState(false);
  const [notice, setNotice] = useState({ text: "", type: "" });

  // 1. Fetch user's exchanges list
  const loadExchanges = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const response = await api.get("/api/v1/exchanges?limit=50&offset=0", authConfig());
      const items = response.data.items || response.data || [];
      setExchanges(items);
      return items;
    } catch (error) {
      setLoadError(errorText(error, "Could not load your exchanges."));
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadExchanges();
  }, [loadExchanges]);

  // 2. Load single exchange detail and partner contact
  const loadDetail = useCallback(async (exchangeId) => {
    setDetailLoading(true);
    setDetailError("");
    setNotice({ text: "", type: "" });
    setContact(null);
    setContactNotice("");

    try {
      const res = await api.get(`/api/v1/exchanges/${exchangeId}`, authConfig());
      setExchangeDetail(res.data);
      if (res.data.due_at) {
        setDueDateInput(res.data.due_at.split("T")[0]);
      } else {
        setDueDateInput("");
      }
    } catch (error) {
      setDetailError(errorText(error, "Could not load exchange details."));
    } finally {
      setDetailLoading(false);
    }

    // Attempt to load partner contact (SR-007 / F-024)
    setContactLoading(true);
    try {
      const contactRes = await api.get(`/api/v1/exchanges/${exchangeId}/contact`, authConfig());
      setContact(contactRes.data);
    } catch (error) {
      if (error?.response?.status === 403) {
        setContactNotice("Contact details are no longer available for cancelled exchanges.");
      } else if (error?.response?.status === 404) {
        setContactNotice("Contact details are only disclosed to mutual exchange participants.");
      } else {
        setContactNotice("Could not load contact details.");
      }
    } finally {
      setContactLoading(false);
    }
  }, []);

  // Open exchange from list or via initialExchangeId prop
  const handleOpenExchange = useCallback((ex) => {
    setSelectedExchange(ex);
    loadDetail(ex.id);
  }, [loadDetail]);

  useEffect(() => {
    if (initialExchangeId && exchanges.length > 0) {
      const target = exchanges.find((e) => e.id === Number(initialExchangeId));
      if (target) {
        handleOpenExchange(target);
      } else {
        // Exchange might not be in the initial page; fetch detail directly
        setSelectedExchange({ id: Number(initialExchangeId) });
        loadDetail(Number(initialExchangeId));
      }
      onClearInitialExchange?.();
    }
  }, [initialExchangeId, exchanges, handleOpenExchange, loadDetail, onClearInitialExchange]);

  function handleBackToList() {
    setSelectedExchange(null);
    setExchangeDetail(null);
    setContact(null);
    setNotice({ text: "", type: "" });
    loadExchanges();
  }

  // 3. Set Due Date (F-025)
  async function handleSetDueDate(event) {
    event.preventDefault();
    if (!dueDateInput) return;

    setNotice({ text: "", type: "" });
    const selectedDate = new Date(`${dueDateInput}T23:59:59Z`);
    if (selectedDate <= new Date()) {
      setNotice({ text: "Due date must be in the future.", type: "error" });
      return;
    }

    setDueDateSaving(true);
    try {
      const res = await api.put(
        `/api/v1/exchanges/${selectedExchange.id}/due-date`,
        { due_at: selectedDate.toISOString() },
        authConfig()
      );
      setExchangeDetail(res.data);
      setNotice({ text: "Agreed due date updated successfully.", type: "success" });
    } catch (error) {
      setNotice({ text: errorText(error, "Could not update due date."), type: "error" });
    } finally {
      setDueDateSaving(false);
    }
  }

  // 4. Lender Handover Confirmation (F-025)
  async function handleConfirmHandover() {
    if (!window.confirm("Confirm that you have physically handed over the book to the borrower?")) {
      return;
    }

    setNotice({ text: "", type: "" });
    setActionBusy(true);
    try {
      const res = await api.post(
        `/api/v1/exchanges/${selectedExchange.id}/handover`,
        {},
        authConfig()
      );
      setExchangeDetail(res.data);
      setNotice({ text: "Handover confirmed! The exchange is now On Loan.", type: "success" });
    } catch (error) {
      setNotice({ text: errorText(error, "Could not confirm handover."), type: "error" });
    } finally {
      setActionBusy(false);
    }
  }

  // 5. Cancellation before Handover (F-025)
  async function handleCancelExchange() {
    if (
      !window.confirm(
        "Are you sure you want to cancel this exchange? The listing will revert to Available and partner contact access will be revoked."
      )
    ) {
      return;
    }

    setNotice({ text: "", type: "" });
    setActionBusy(true);
    try {
      const res = await api.post(
        `/api/v1/exchanges/${selectedExchange.id}/cancel`,
        {},
        authConfig()
      );
      setExchangeDetail(res.data);
      setContact(null);
      setContactNotice("Contact access has been revoked for this cancelled exchange.");
      setNotice({
        text: "Exchange was cancelled. The book listing has returned to Available.",
        type: "success",
      });
    } catch (error) {
      setNotice({ text: errorText(error, "Could not cancel exchange."), type: "error" });
    } finally {
      setActionBusy(false);
    }
  }

  // Filter exchanges list
  const filteredExchanges = exchanges.filter((ex) => {
    if (tabFilter === "ACTIVE") return ex.state === "ACCEPTED" || ex.state === "ON_LOAN";
    if (tabFilter === "RETURNED") return ex.state === "RETURNED";
    if (tabFilter === "CANCELLED") return ex.state === "CANCELLED";
    return true;
  });

  return (
    <section className="browse-page exchanges-page">
      <div className="browse-heading">
        <span className="eyebrow">Peer-to-Peer</span>
        <h1>Book Exchanges</h1>
        <p>Manage your accepted book loans, agreed due dates, handover, and partner contact details.</p>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* DETAIL VIEW                                                   */}
      {/* ------------------------------------------------------------- */}
      {selectedExchange ? (
        <div className="exchange-detail-container">
          <button className="back-link-btn" type="button" onClick={handleBackToList}>
            ← Back to all exchanges
          </button>

          {notice.text && (
            <div className={`message ${notice.type === "success" ? "success" : "error"}`}>
              {notice.text}
            </div>
          )}

          {detailLoading ? (
            <p className="loading-state">Loading exchange details...</p>
          ) : detailError ? (
            <div className="message error">
              <p>{detailError}</p>
              <button className="secondary-btn" type="button" onClick={() => loadDetail(selectedExchange.id)}>
                Retry
              </button>
            </div>
          ) : (
            exchangeDetail && (
              <div className="exchange-detail-layout">
                {/* Header Summary */}
                <div className="exchange-header-card">
                  <div className="exchange-header-info">
                    <span className="exchange-id-tag">Exchange #{exchangeDetail.id}</span>
                    <h2>{selectedExchange.book_title || "Book Exchange"}</h2>
                    {selectedExchange.book_author && (
                      <p className="author-line">by {selectedExchange.book_author}</p>
                    )}
                    <div className="exchange-badges">
                      <span className={`badge ${STATE_LABELS[exchangeDetail.state]?.className || ""}`}>
                        {STATE_LABELS[exchangeDetail.state]?.label || exchangeDetail.state}
                      </span>
                      <span className="badge role-badge">
                        You are the {selectedExchange.role === "lender" ? "Lender" : "Borrower"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="exchange-cards-grid">
                  {/* Card 1: Partner Contact Disclosure (SR-007 / F-024) */}
                  <div className="exchange-card contact-card">
                    <div className="card-header">
                      <h3>Partner Contact Details</h3>
                      <span className="privacy-chip">Mutual Acceptance Verified</span>
                    </div>
                    {contactLoading ? (
                      <p className="loading-text">Loading contact details...</p>
                    ) : contact ? (
                      <div className="contact-details-grid">
                        <div className="contact-item">
                          <label>Partner Name</label>
                          <strong>{contact.name}</strong>
                        </div>
                        <div className="contact-item">
                          <label>Email Address</label>
                          <a href={`mailto:${contact.email}`} className="contact-email">
                            {contact.email}
                          </a>
                        </div>
                        {contact.department && (
                          <div className="contact-item">
                            <label>Department</label>
                            <span>{contact.department}</span>
                          </div>
                        )}
                        <div className="contact-item">
                          <label>Campus Location</label>
                          <span>{contact.location}</span>
                        </div>
                        <p className="contact-privacy-note">
                          ✓ Disclosed exclusively to mutual participants of this active exchange.
                        </p>
                      </div>
                    ) : (
                      <div className="contact-revoked-banner">
                        <p>{contactNotice || "Contact information is restricted."}</p>
                      </div>
                    )}
                  </div>

                  {/* Card 2: Agreed Due Date (F-025) */}
                  <div className="exchange-card due-date-card">
                    <div className="card-header">
                      <h3>Agreed Due Date</h3>
                    </div>
                    <div className="due-date-body">
                      <p className="current-due-date">
                        Current Due Date:{" "}
                        <strong>{formatDate(exchangeDetail.due_at)}</strong>
                      </p>

                      {exchangeDetail.state === "ACCEPTED" ? (
                        <form onSubmit={handleSetDueDate} className="due-date-form">
                          <label htmlFor="dueDateInput">
                            Set or adjust return due date:
                          </label>
                          <div className="due-date-input-group">
                            <input
                              id="dueDateInput"
                              type="date"
                              min={getTomorrowMinDate()}
                              value={dueDateInput}
                              onChange={(e) => setDueDateInput(e.target.value)}
                              required
                            />
                            <button
                              className="primary-btn"
                              type="submit"
                              disabled={dueDateSaving || actionBusy}
                            >
                              {dueDateSaving ? "Saving..." : "Save Due Date"}
                            </button>
                          </div>
                          <span className="form-hint">
                            Must be a future date agreed upon with your exchange partner.
                          </span>
                        </form>
                      ) : (
                        <p className="form-hint">
                          {exchangeDetail.state === "ON_LOAN"
                            ? "Due date is fixed during active loan."
                            : "Due date cannot be changed in this status."}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Card 3: Handover & Actions (F-025) */}
                  <div className="exchange-card actions-card">
                    <div className="card-header">
                      <h3>Exchange Actions</h3>
                    </div>
                    <div className="actions-card-body">
                      {exchangeDetail.state === "ACCEPTED" && (
                        <>
                          {selectedExchange.role === "lender" ? (
                            <div className="action-block">
                              <h4>Lender Handover</h4>
                              <p>
                                Once you have physically given the book to the borrower, confirm handover to mark the exchange as On Loan.
                              </p>
                              {!exchangeDetail.due_at && (
                                <p className="action-warning">
                                  ⚠ An agreed due date is required before confirming handover.
                                </p>
                              )}
                              <button
                                className="primary-btn confirm-handover-btn"
                                type="button"
                                disabled={!exchangeDetail.due_at || actionBusy}
                                onClick={handleConfirmHandover}
                              >
                                {actionBusy ? "Processing..." : "Confirm Handover to Borrower"}
                              </button>
                            </div>
                          ) : (
                            <div className="action-block">
                              <h4>Awaiting Handover</h4>
                              <p>
                                Meet your lender ({selectedExchange.partner_name || "partner"}) at the agreed location. The lender will confirm handover once the book is received.
                              </p>
                            </div>
                          )}

                          <div className="action-block cancel-block">
                            <h4>Cancel Exchange</h4>
                            <p>
                              Either participant may cancel this exchange prior to handover. The listing will immediately return to Available.
                            </p>
                            <button
                              className="danger-btn"
                              type="button"
                              disabled={actionBusy}
                              onClick={handleCancelExchange}
                            >
                              {actionBusy ? "Cancelling..." : "Cancel Exchange"}
                            </button>
                          </div>
                        </>
                      )}

                      {exchangeDetail.state === "ON_LOAN" && (
                        <div className="action-block on-loan-block">
                          <h4>Currently On Loan</h4>
                          <p>
                            Handover confirmed on {formatDate(exchangeDetail.handover_confirmed_at)}.
                          </p>
                          <p>
                            Book should be returned on or before <strong>{formatDate(exchangeDetail.due_at)}</strong>.
                          </p>
                        </div>
                      )}

                      {exchangeDetail.state === "CANCELLED" && (
                        <div className="action-block cancelled-block">
                          <h4>Exchange Cancelled</h4>
                          <p>
                            Cancelled on {formatDate(exchangeDetail.cancelled_at)}. The book listing has returned to the public marketplace.
                          </p>
                        </div>
                      )}

                      {exchangeDetail.state === "RETURNED" && (
                        <div className="action-block returned-block">
                          <h4>Exchange Completed</h4>
                          <p>The book return has been confirmed. Thank you for sharing!</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card 4: Event Timeline */}
                  <div className="exchange-card timeline-card">
                    <div className="card-header">
                      <h3>Exchange Timeline</h3>
                    </div>
                    {exchangeDetail.events && exchangeDetail.events.length > 0 ? (
                      <ol className="timeline-list">
                        {exchangeDetail.events.map((evt) => (
                          <li key={evt.id} className="timeline-item">
                            <div className="timeline-dot" />
                            <div className="timeline-content">
                              <strong>
                                {evt.event_type === "DUE_DATE_SET"
                                  ? "Agreed due date set"
                                  : evt.event_type === "HANDOVER_CONFIRMED"
                                  ? "Handover confirmed (On Loan)"
                                  : evt.event_type === "CANCELLED"
                                  ? "Exchange cancelled before handover"
                                  : evt.event_type}
                              </strong>
                              <span className="timeline-time">{formatDate(evt.created_at)}</span>
                            </div>
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <p className="timeline-empty">Exchange initiated upon mutual acceptance.</p>
                    )}
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      ) : (
        /* ------------------------------------------------------------- */
        /* LIST VIEW                                                     */
        /* ------------------------------------------------------------- */
        <div className="exchanges-list-container">
          <div className="exchanges-filter-bar">
            <div className="filter-tabs" role="tablist">
              {["ALL", "ACTIVE", "RETURNED", "CANCELLED"].map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={`tab-btn ${tabFilter === tab ? "active" : ""}`}
                  onClick={() => setTabFilter(tab)}
                >
                  {tab === "ALL"
                    ? `All (${exchanges.length})`
                    : tab === "ACTIVE"
                    ? "Active"
                    : tab === "RETURNED"
                    ? "Returned"
                    : "Cancelled"}
                </button>
              ))}
            </div>

            <button className="secondary-btn refresh-btn" type="button" onClick={loadExchanges}>
              Refresh
            </button>
          </div>

          {loadError && (
            <div className="message error">
              <p>{loadError}</p>
              <button className="secondary-btn" type="button" onClick={loadExchanges}>
                Try again
              </button>
            </div>
          )}

          {loading ? (
            <p className="loading-state">Loading your exchanges...</p>
          ) : filteredExchanges.length === 0 ? (
            <div className="empty-state-box">
              <h3>No exchanges found</h3>
              <p>
                {tabFilter === "ALL"
                  ? "You don't have any book exchanges yet. Mutual acceptance of a book match creates an active exchange."
                  : `No ${tabFilter.toLowerCase()} exchanges.`}
              </p>
              <button className="primary-btn" type="button" onClick={() => onNavigate?.("requests")}>
                View My Requests
              </button>
            </div>
          ) : (
            <ul className="exchanges-list">
              {filteredExchanges.map((ex) => {
                const stateInfo = STATE_LABELS[ex.state] || { label: ex.state, className: "" };
                const isLender = ex.role === "lender";
                return (
                  <li key={ex.id} className="exchange-card-item">
                    <div className="exchange-card-top">
                      <div>
                        <span className="exchange-num">Exchange #{ex.id}</span>
                        <h3 className="exchange-book-title">{ex.book_title || "Book Exchange"}</h3>
                        {ex.book_author && (
                          <span className="exchange-book-author">by {ex.book_author}</span>
                        )}
                      </div>
                      <div className="exchange-card-tags">
                        <span className={`badge ${stateInfo.className}`}>{stateInfo.label}</span>
                        <span className="badge role-badge">
                          {isLender ? "Lending" : "Borrowing"}
                        </span>
                      </div>
                    </div>

                    <div className="exchange-card-meta">
                      <div className="meta-item">
                        <label>Partner:</label>
                        <span>{ex.partner_name || ex.partner_display_name || "Partner"}</span>
                      </div>
                      <div className="meta-item">
                        <label>Due Date:</label>
                        <span>{ex.due_at ? formatDate(ex.due_at) : "Not agreed yet"}</span>
                      </div>
                      <div className="meta-item">
                        <label>Created:</label>
                        <span>{formatDate(ex.created_at)}</span>
                      </div>
                    </div>

                    <div className="exchange-card-actions">
                      <button
                        className="primary-btn open-exchange-btn"
                        type="button"
                        onClick={() => handleOpenExchange(ex)}
                      >
                        Open Exchange Details →
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

export default ExchangesPage;
