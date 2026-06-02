import { useState } from "react";
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle,
  MenuItem, Stack, TextField, Typography,
} from "@mui/material";
import { createUser } from "../api/client";

export default function UserDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("hr");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  const reset = () => {
    setEmail(""); setFullName(""); setPassword(""); setRole("hr");
    setError(""); setOk("");
  };

  const submit = async () => {
    setError(""); setOk("");
    if (!email.trim() || password.length < 8) {
      setError("Enter an email and a password of at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      const u = await createUser(email.trim(), password, fullName.trim(), role);
      setOk(`Created ${u.email} (${u.role}). They can sign in now.`);
      setEmail(""); setFullName(""); setPassword(""); setRole("hr");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not create user.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={() => { reset(); onClose(); }} maxWidth="xs" fullWidth>
      <DialogTitle>Add a user</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Create a sign-in account. HR users can screen candidates; admins can also
          manage users.
        </Typography>
        <Stack spacing={2}>
          {error && <Alert severity="error">{error}</Alert>}
          {ok && <Alert severity="success">{ok}</Alert>}
          <TextField label="Full name" size="small" value={fullName}
            onChange={(e) => setFullName(e.target.value)} />
          <TextField label="Email" size="small" value={email}
            onChange={(e) => setEmail(e.target.value)} />
          <TextField label="Temporary password" type="password" size="small" value={password}
            helperText="At least 8 characters"
            onChange={(e) => setPassword(e.target.value)} />
          <TextField select label="Role" size="small" value={role}
            onChange={(e) => setRole(e.target.value)}>
            <MenuItem value="hr">HR (screen candidates)</MenuItem>
            <MenuItem value="admin">Admin (also manage users)</MenuItem>
          </TextField>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => { reset(); onClose(); }}>Close</Button>
        <Button variant="contained" onClick={submit} disabled={busy}>
          {busy ? "Creating…" : "Create user"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
