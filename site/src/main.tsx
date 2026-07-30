import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import "./styles/global.css";

// HashRouter, not BrowserRouter. The site is deployed to static hosting
// (Hugging Face static Space), which serves files literally and has no rewrite
// rule — so a direct load or refresh of /method returned a hard 404, verified
// against the live deployment. Hash routing keeps every route in the fragment,
// so it works on any static host with no server configuration.
//
// Consequence: in-page anchors cannot use href="#id", because the hash now
// belongs to the router. Those are scrollToId() calls instead — see Hero.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>
);
