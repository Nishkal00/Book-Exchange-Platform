import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { errorText } from "./RequestsPage.jsx";

function authConfig() {
  return {
    headers: { Authorization: `Bearer ${localStorage.getItem("bep_token")}` },
  };
}

const EVENT_TYPE_LABELS = {
  EXCHANGE_UPDATED: { label: "Exchange", className: "badge-exchange" },
  MATCH_FOUND: { label: "Match Found", className: "badge-match" },
  PARTNER_DECISION: { label: "Partner Decision", className: "badge-decision" },
};

function formatTime(dateStr) {
  if (!dateStr) return "";
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

function NotificationsPage({ user, onNavigate, onNotificationRead }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [filter, setFilter] = useState("ALL"); // ALL, UNREAD
  const [busyId, setBusyId] = useState(null);
  const [markingAll, setMarkingAll] = useState(false);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const response = await api.get("/api/v1/notifications?limit=50&offset=0", authConfig());
      setNotifications(response.data.items || []);
      setUnreadCount(response.data.unread_count || 0);
      setTotal(response.data.total || 0);
    } catch (error) {
      setLoadError(errorText(error, "Could not load notifications."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  async function handleMarkRead(id) {
    setBusyId(id);
    try {
      await api.patch(`/api/v1/notifications/${id}/read`, {}, authConfig());
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
      onNotificationRead?.();
    } catch (error) {
      console.error("Failed to mark notification as read", error);
    } finally {
      setBusyId(null);
    }
  }

  async function handleMarkAllRead() {
    const unreadItems = notifications.filter((n) => !n.is_read);
    if (unreadItems.length === 0) return;

    setMarkingAll(true);
    try {
      await Promise.all(
        unreadItems.map((n) => api.patch(`/api/v1/notifications/${n.id}/read`, {}, authConfig()))
      );
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      onNotificationRead?.();
    } catch (error) {
      console.error("Failed to mark all as read", error);
    } finally {
      setMarkingAll(false);
    }
  }

  const filtered = notifications.filter((n) => {
    if (filter === "UNREAD") return !n.is_read;
    return true;
  });

  return (
    <section className="browse-page notifications-page">
      <div className="browse-heading">
        <span className="eyebrow">Activity</span>
        <h1>In-App Notifications</h1>
        <p>Stay updated on book matches, exchange decisions, agreed due dates, and handovers.</p>
      </div>

      <div className="notifications-toolbar">
        <div className="filter-tabs">
          <button
            type="button"
            className={`tab-btn ${filter === "ALL" ? "active" : ""}`}
            onClick={() => setFilter("ALL")}
          >
            All ({total})
          </button>
          <button
            type="button"
            className={`tab-btn ${filter === "UNREAD" ? "active" : ""}`}
            onClick={() => setFilter("UNREAD")}
          >
            Unread ({unreadCount})
          </button>
        </div>

        <div className="notifications-toolbar-actions">
          {unreadCount > 0 && (
            <button
              className="secondary-btn"
              type="button"
              disabled={markingAll}
              onClick={handleMarkAllRead}
            >
              {markingAll ? "Marking..." : "Mark all as read"}
            </button>
          )}
          <button
            className="secondary-btn refresh-btn"
            type="button"
            onClick={loadNotifications}
          >
            Refresh
          </button>
        </div>
      </div>

      {loadError && (
        <div className="message error">
          <p>{loadError}</p>
          <button className="secondary-btn" type="button" onClick={loadNotifications}>
            Try again
          </button>
        </div>
      )}

      {loading ? (
        <p className="loading-state">Loading your notifications...</p>
      ) : filtered.length === 0 ? (
        <div className="empty-state-box">
          <h3>No notifications</h3>
          <p>
            {filter === "UNREAD"
              ? "You have caught up with all notifications."
              : "When a book is matched or an exchange status changes, notifications will appear here."}
          </p>
        </div>
      ) : (
        <ul className="notifications-list">
          {filtered.map((item) => {
            const badgeInfo = EVENT_TYPE_LABELS[item.event_type] || {
              label: item.event_type,
              className: "",
            };
            const isExchangeNotice =
              item.event_type === "EXCHANGE_UPDATED" ||
              item.message?.toLowerCase().includes("exchange");
            const isMatchNotice =
              item.event_type === "MATCH_FOUND" ||
              item.event_type === "PARTNER_DECISION" ||
              item.message?.toLowerCase().includes("match");

            return (
              <li
                key={item.id}
                className={`notification-item ${item.is_read ? "read" : "unread"}`}
              >
                <div className="notification-status-indicator">
                  {!item.is_read && <span className="unread-dot" title="Unread" />}
                </div>

                <div className="notification-body">
                  <div className="notification-meta-top">
                    <span className={`badge ${badgeInfo.className}`}>{badgeInfo.label}</span>
                    <span className="notification-time">{formatTime(item.created_at)}</span>
                  </div>

                  <p className="notification-message">{item.message}</p>

                  <div className="notification-actions">
                    {!item.is_read && (
                      <button
                        className="mark-read-btn"
                        type="button"
                        disabled={busyId === item.id}
                        onClick={() => handleMarkRead(item.id)}
                      >
                        {busyId === item.id ? "Saving..." : "Mark as read"}
                      </button>
                    )}

                    {isExchangeNotice && (
                      <button
                        className="primary-btn nav-link-btn"
                        type="button"
                        onClick={() => {
                          if (!item.is_read) handleMarkRead(item.id);
                          onNavigate?.("exchanges");
                        }}
                      >
                        Go to Exchanges →
                      </button>
                    )}

                    {!isExchangeNotice && isMatchNotice && (
                      <button
                        className="secondary-btn nav-link-btn"
                        type="button"
                        onClick={() => {
                          if (!item.is_read) handleMarkRead(item.id);
                          onNavigate?.("requests");
                        }}
                      >
                        Go to Requests →
                      </button>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default NotificationsPage;
