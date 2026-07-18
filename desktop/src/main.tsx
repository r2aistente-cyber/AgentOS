import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import StandaloneChat from "./StandaloneChat";

// Ruteo mínimo por query-param (funciona en dev y en el bundle de Tauri):
// ?view=chat -> ventana de chat nativa; cualquier otra cosa -> Hub completo.
const isChatWindow =
  new URLSearchParams(window.location.search).get("view") === "chat";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {isChatWindow ? <StandaloneChat /> : <App />}
  </React.StrictMode>,
);
