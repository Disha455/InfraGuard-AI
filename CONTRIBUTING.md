# Contribution Guide

Please follow these rules while working on the project.

---

# Git Workflow

Never work directly on the main branch.

Create your own branch.

Example

```bash
git checkout -b rahul-dashboard
```

or

```bash
git checkout -b sneha-auth
```

---

# Before Coding

Always pull latest changes.

```bash
git pull origin main
```

---

# Commit

```bash
git add .
```

```bash
git commit -m "Implemented dashboard module"
```

---

# Push

```bash
git push origin your-branch-name
```

Example

```bash
git push origin rahul-dashboard
```

---

# Do NOT

- Push directly to main
- Rename folders
- Change API endpoints
- Delete existing code
- Modify prediction workflow without discussion

---

# Before Committing

Run

```bash
flutter analyze
```

Fix all warnings/errors before pushing.

---

# Communication

If your work requires modifying shared files, inform the team first.

Examples

- AppRouter
- ApiService
- PredictionResponseModel
- AppTheme
- Backend Routes

---

# Code Style

- Keep widgets modular.
- Avoid duplicate code.
- Follow existing folder structure.
- Reuse AppColors and AppTheme.