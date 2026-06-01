import { Box, Button, Container, Stack, Typography } from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { omni } from "../theme/theme";

export default function Welcome({ onStart }: { onStart: () => void }) {
  const name = localStorage.getItem("name") || "there";
  return (
    <Box
      sx={{
        minHeight: "100vh",
        position: "relative",
        overflow: "hidden",
        display: "grid",
        placeItems: "center",
        background: `radial-gradient(1100px 600px at 85% -5%, ${omni.blue}14 0%, transparent 55%),
                     radial-gradient(900px 500px at -5% 105%, ${omni.amber}1f 0%, transparent 55%),
                     #f4f6fb`,
      }}
    >
      {/* Decorative arc echoing the logo */}
      <Box aria-hidden sx={{
        position: "absolute", top: -120, right: -120, width: 360, height: 360,
        borderRadius: "50%", border: `28px solid ${omni.amber}`, opacity: 0.12,
        borderRightColor: "transparent", borderBottomColor: "transparent",
        transform: "rotate(25deg)",
      }} />
      <Box aria-hidden sx={{
        position: "absolute", bottom: -140, left: -100, width: 320, height: 320,
        borderRadius: "50%", border: `24px solid ${omni.blue}`, opacity: 0.08,
        borderLeftColor: "transparent", borderTopColor: "transparent",
      }} />

      <Container maxWidth="sm" sx={{ textAlign: "center", position: "relative", zIndex: 1 }}>
        <Stack spacing={3} alignItems="center">
          <Box
            component="img"
            src="/logo.png"
            alt="Omni Control Technology"
            sx={{ width: 132, height: "auto", filter: "drop-shadow(0 6px 14px rgba(38,53,140,0.18))" }}
          />
          <Box>
            <Typography variant="overline" sx={{ color: omni.slate, letterSpacing: "0.18em" }}>
              Omni Control Technology
            </Typography>
            <Typography variant="h3" sx={{ mt: 0.5, lineHeight: 1.05 }}>
              Left Hand&nbsp;Man
            </Typography>
            <Box sx={{
              width: 64, height: 4, borderRadius: 2, mx: "auto", mt: 1.5,
              background: `linear-gradient(90deg, ${omni.amber}, ${omni.blue})`,
            }} />
          </Box>

          <Typography variant="h6" sx={{ fontWeight: 500, color: "text.secondary", maxWidth: 440 }}>
            Your right hand's right hand for hiring. Paste a job, drop in resumes,
            and get a ranked shortlist with the reasoning behind every score.
          </Typography>

          <Stack direction="row" spacing={3} sx={{ pt: 1 }}>
            {[
              ["1", "Add a job"],
              ["2", "Upload resumes"],
              ["3", "Review the ranking"],
            ].map(([n, label]) => (
              <Stack key={n} alignItems="center" spacing={0.75} sx={{ width: 96 }}>
                <Box sx={{
                  width: 36, height: 36, borderRadius: "50%", display: "grid", placeItems: "center",
                  bgcolor: "#fff", border: `2px solid ${omni.amber}`, color: omni.blue, fontWeight: 800,
                }}>{n}</Box>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
              </Stack>
            ))}
          </Stack>

          <Button
            size="large"
            variant="contained"
            endIcon={<ArrowForwardIcon />}
            onClick={onStart}
            sx={{ mt: 1, px: 4, py: 1.25, borderRadius: 3, fontSize: "1rem" }}
          >
            Get started
          </Button>
          <Typography variant="caption" color="text.secondary">
            Welcome back, {name}.
          </Typography>
        </Stack>
      </Container>
    </Box>
  );
}
