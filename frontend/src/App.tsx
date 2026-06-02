import { useState } from "react";
import { isAuthed } from "./api/client";
import Login from "./pages/Login";
import Welcome from "./pages/Welcome";
import Dashboard from "./pages/Dashboard";

type View = "welcome" | "dashboard";

export default function App() {
  const [authed, setAuthed] = useState(isAuthed());
  const [view, setView] = useState<View>("welcome");

  if (!authed) {
    return <Login onLogin={() => { setAuthed(true); setView("welcome"); }} />;
  }
  if (view === "welcome") {
    return <Welcome onStart={() => setView("dashboard")} />;
  }
  return (
    <Dashboard
      onHome={() => setView("welcome")}
      onLogout={() => { setAuthed(false); setView("welcome"); }}
    />
  );
}
