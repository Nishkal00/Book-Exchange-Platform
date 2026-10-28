import { useEffect, useState } from "react";
import { api } from "./api.js";

// Scaffold only: Ravish builds the navbar, routes and pages on top of this (BEP-20..22).
export default function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    api
      .get("/health")
      .then((res) => setStatus(res.data.status))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <main className="container">
      <h1>Book Exchange Platform</h1>
      <p>
        API status: <strong>{status}</strong>
      </p>
    </main>
  );
}
