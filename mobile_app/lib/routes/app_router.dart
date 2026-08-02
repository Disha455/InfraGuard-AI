// InfraGuard AI — Application Router.
//
// Centralises all named route definitions so that navigation calls
// throughout the app use constants rather than raw strings.
//
// Planned routes:
//   /           → HomeScreen (or PredictionPage for MVP)
//   /result     → ResultPage (receives PredictionResult as argument)
//   /history    → HistoryPage (past prediction runs)
//   /settings   → SettingsPage (API base URL, thresholds)
//
// Preferred implementation: go_router or Navigator 2.0 with GoRoute.
// The specific package will be added to pubspec.yaml in the next task.
