import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { login } from "../api/client";
import { omni } from "../theme/theme";

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("admin@omnicontrol.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      onLogin();
    } catch {
      setError("Incorrect email or password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{
      minHeight: "100vh", display: "grid", placeItems: "center", p: 2,
      background: `radial-gradient(1000px 480px at 80% -10%, ${omni.amber}22 0%, transparent 55%),
                   radial-gradient(900px 520px at 10% 110%, ${omni.blue}26 0%, transparent 55%),
                   #1B2868`,
    }}>
      <Paper elevation={0} sx={{ p: 4, width: 384, borderRadius: 4, border: "none" }}>
        <Stack alignItems="center" spacing={1} sx={{ mb: 2.5 }}>
          <Box component="img" src="/logo.png" alt="Omni Control" sx={{ width: 88 }} />
          <Typography variant="h4" sx={{ mt: 1 }}>Left Hand Man</Typography>
          <Typography variant="body2" color="text.secondary">
            Resume Ranking &amp; Candidate Screening
          </Typography>
        </Stack>
        <Stack spacing={2}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField label="Email" value={email} size="small"
            onChange={(e) => setEmail(e.target.value)} />
          <TextField label="Password" type="password" value={password} size="small"
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()} />
          <Button variant="contained" onClick={submit} disabled={busy} size="large"
            sx={{ py: 1.1 }}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
