# 🤝 InfraGuard-AI Contribution Guidelines

Thank you for contributing to InfraGuard-AI! To maintain code quality, consistency, and zero regressions, please adhere to these guidelines.

---

## 1. Branching Strategy

- **`main` / `develop`**: Protected branches. Never commit directly to `main` or `develop`.
- **Feature Branches**: Branch off `develop` using standard naming conventions:
  - `feature/<name>-<module>` (e.g. `feature/disha-admin-analytics`)
  - `fix/<name>-<issue>` (e.g. `fix/image-thumbnail-sync`)

---

## 2. Pre-Commit Checklist

Before staging and committing your code, you **MUST** run the automated test suites:

### A. Mobile Application (Flutter)
```bash
cd mobile_app
flutter analyze     # MUST report 0 issues
flutter test        # All 71 tests MUST pass
```

### B. Backend Services (FastAPI & Pytest)
```powershell
.\.venv\Scripts\python -m pytest backend/tests  # All 52 tests MUST pass
```

---

## 3. Commit Message Standards

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat(ui): add ambient pastel gradient and dynamic server dialog`
- `fix(history): resolve thumbnail URL path against configured base URL`
- `perf(backend): optimize SQLite analytics aggregation queries`
- `docs(readme): update system architecture and database schema reference`

---

## 4. Code Standards & Architecture Guidelines

### Flutter / Dart
- **Theming**: Never hardcode colors or hex codes directly in widget trees. All colors, gradients, and elevation tokens must reference `AppColors` from `lib/core/theme/app_colors.dart`.
- **Networking**: All HTTP communication must go through `ApiService` using dynamic endpoints from `ApiEndpoints.baseUrl`. Never hardcode raw IP strings.
- **State & Separation of Concerns**: Keep business logic, models, and presentation widgets in their respective feature folders under `lib/features/`.

### Backend / Python
- **Type Annotations**: All functions and route handlers must include explicit type hints (`list[str]`, `dict[str, Any]`, `float | None`).
- **Database Operations**: Perform database operations using context managers (`with self._get_connection() as conn:`) with parameterized queries to prevent SQL injection.
- **API Models**: Define request/response payloads with Pydantic schemas in `backend/schemas/`.

---

## 5. Submitting Pull Requests

1. Rebase your feature branch on the latest `origin/develop`:
   ```bash
   git fetch origin
   git rebase origin/develop
   ```
2. Resolve any merge conflicts cleanly.
3. Push to your feature branch:
   ```bash
   git push origin <your-branch-name>
   ```
4. Open a Pull Request with a clear description of:
   - What features or fixes were implemented.
   - Test results (confirmation that `flutter test` and `pytest` passed).
   - Screenshots/recordings if UI changes were introduced.