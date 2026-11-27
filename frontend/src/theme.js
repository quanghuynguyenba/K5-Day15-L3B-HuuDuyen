import { createTheme } from "@mui/material/styles";

// Shared palette from the updated Stitch export. CSS and MUI use these tokens.
export const designTokens = Object.freeze({
  primary: "#0369B2",
  primaryContainer: "#2A6D99",
  primaryTint: "#E3F8FC",
  iceCyan: "#B9F0F9",
  slateCerulean: "#78AEC6",
  background: "#FAFCFB",
  surface: "#FFFFFF",
  surfaceLow: "#F1F6F8",
  surfaceContainer: "#E8F0F3",
  text: "#171C1F",
  textSecondary: "#33414A",
  outline: "#5A7382",
  outlineVariant: "#B3CCD8",
  selected: "#FD651E",
  selectedText: "#A73A00",
  selectedTint: "#FFF0E8",
  error: "#BA1A1A",
  success: "#15803D",
  warning: "#B45309",
});

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: designTokens.primary,
      dark: designTokens.primaryContainer,
      light: designTokens.iceCyan,
      contrastText: "#fff",
    },
    secondary: {
      main: designTokens.selectedText,
      light: designTokens.selectedTint,
    },
    background: {
      default: designTokens.background,
      paper: designTokens.surface,
    },
    text: { primary: designTokens.text, secondary: designTokens.textSecondary },
    divider: designTokens.outlineVariant,
    error: { main: designTokens.error },
    success: { main: designTokens.success },
    warning: { main: designTokens.warning },
  },
  typography: {
    fontFamily: 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif',
    button: { textTransform: "none", fontWeight: 500 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { minWidth: 0 } },
    },
    MuiIconButton: { defaultProps: { size: "small" } },
    MuiTooltip: { defaultProps: { arrow: true } },
    MuiCssBaseline: {
      styleOverrides: {
        ":root": Object.fromEntries(
          Object.entries(designTokens).map(([key, value]) => [
            `--color-${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`,
            value,
          ]),
        ),
        "::selection": {
          backgroundColor: designTokens.iceCyan,
          color: designTokens.primaryContainer,
        },
      },
    },
  },
});
