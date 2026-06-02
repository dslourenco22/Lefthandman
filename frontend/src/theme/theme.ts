import { createTheme } from "@mui/material/styles";

// Palette drawn from the Omni Control logo:
//  - royal blue wordmark, golden-amber arc, slate-gray subtext.
export const omni = {
  blue: "#26358C",
  blueDark: "#1B2868",
  amber: "#F2A900",
  amberDark: "#D6940A",
  slate: "#5A6472",
  mist: "#eef1f7",
};

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: omni.blue, dark: omni.blueDark, contrastText: "#ffffff" },
    secondary: { main: omni.amber, dark: omni.amberDark, contrastText: "#1b2034" },
    background: { default: "#f4f6fb", paper: "#ffffff" },
    text: { primary: "#1b2034", secondary: omni.slate },
    success: { main: "#2f855a" },
    warning: { main: "#b7791f" },
    error: { main: "#c53030" },
    info: { main: omni.blue },
    divider: "#e3e8f1",
  },
  typography: {
    fontFamily: '"Public Sans", system-ui, sans-serif',
    h3: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600, letterSpacing: "-0.02em" },
    h4: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600, letterSpacing: "-0.01em" },
    h5: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
    h6: { fontWeight: 700, letterSpacing: "-0.005em" },
    button: { textTransform: "none", fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: "none", border: "1px solid #e6eaf3" },
      },
    },
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 700, color: omni.slate } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
  },
});
