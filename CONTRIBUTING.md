# Contributing to ClearSight 2.0 RCA Dashboard

Thank you for your interest in contributing to the ClearSight RCA Dashboard project!

## 🔒 Project Status

This is an **internal Merck/MSD project** developed during a software engineering internship.

**Note:** This repository is primarily for:

- Portfolio demonstration
- Documentation purposes
- Knowledge sharing within the organization

## 📋 Guidelines for Internal Contributors

If you're a Merck/MSD team member working on this project:

### Getting Started

1. Read the [Quick Start Guide](docs/QUICK_START.md)
2. Review the [Architecture Documentation](docs/ARCHITECTURE_DIAGRAMS.md)
3. Set up your development environment
4. Contact the project team via Slack: `#clearsight-rca-dashboard`

### Development Workflow

1. **Create a branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

   - Follow existing code patterns
   - Add docstrings to all functions
   - Include type hints
   - Update tests if applicable

3. **Test your changes**

   ```bash
   # Run ETL with mock CloudWatch
   python scripts/run_rca_etl.py --mock-cloudwatch

   # Test API endpoints
   python -m uvicorn src.api.main:app --reload
   ```

4. **Commit with clear messages**

   ```bash
   git add .
   git commit -m "feat: Add user session grouping to user_journey transformer"
   ```

5. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Standards

- **Python Style:** Follow PEP 8
- **Docstrings:** Use Google-style docstrings
- **Type Hints:** Use type hints for all function parameters and returns
- **Error Handling:** Include try/except blocks with meaningful error messages
- **Comments:** Explain "why", not "what"

### Commit Message Format

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Areas for Contribution

#### 🔴 High Priority

- Power BI dashboard development (5 pages)
- OKR validation testing
- Production deployment guide

#### 🟡 Medium Priority

- Additional error categorization patterns
- Performance optimization for large datasets
- Enhanced CloudWatch query filters

#### 🟢 Nice to Have

- Unit tests for transformers
- Integration tests for ETL pipeline
- Additional API endpoints

## 🐛 Reporting Issues

If you encounter bugs or have feature requests:

1. **Check existing issues** - Avoid duplicates
2. **Create detailed issue** with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Screenshots/logs if applicable

## 📞 Contact

**Project Team:**

- **Slack:** `#clearsight-rca-dashboard`
- **Email:** Contact your manager for team contacts

## 📄 License

This is proprietary software owned by Merck/MSD. For internal use only.

---

**Note:** External contributions are not accepted at this time. This repository is for internal collaboration and portfolio demonstration purposes.
