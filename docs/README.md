# Documentation Index

This directory contains all permanent documentation for the Batch File Processor project.

## Directory Structure

```
docs/
├── user-guide/        # End-user documentation
├── testing/           # Testing guides and documentation
├── migrations/        # Database migration guides
├── architecture/      # Architecture and design documents
├── api/              # API specifications
├── design/           # Detailed design specifications
└── archive/          # Historical documents and session summaries
```

## Quick Navigation

### For Users
- **[User Guide](user-guide/)** - EDI format configuration, quick reference, troubleshooting
  - [EDI Format Guide](user-guide/EDI_FORMAT_GUIDE.md)
  - [Quick Reference](user-guide/QUICK_REFERENCE.md)
  - [Launch Troubleshooting](user-guide/LAUNCH_TROUBLESHOOTING.md)

### For Developers
- **[Testing Guide](testing/)** - Test suite documentation
  - [Testing Overview](testing/TESTING.md)
  - [Testing Best Practices](testing/TESTING_BEST_PRACTICES.md)
  - [Qt Testing Guide](testing/QT_TESTING_GUIDE.md)
  - [Corpus Testing Guide](testing/CORPUS_TESTING_GUIDE.md)
- **[Architecture](architecture/)** - System design and architecture
- **[API Documentation](api/)** - API contracts and specifications

### For Database Work
- **[Migration Guides](migrations/)** - Database migration documentation
  - [Automatic Migration Guide](migrations/AUTOMATIC_MIGRATION_GUIDE.md)
  - [Database Migration Guide](migrations/DATABASE_MIGRATION_GUIDE.md)

### Design Documentation
Located in `docs/` root and `design/` subdirectory:
- [Architecture](ARCHITECTURE.md)
- [Data Flow](DATA_FLOW.md)
- [Processing Pipeline](PROCESSING_PIPELINE.md)
- [Plugin Architecture](PLUGIN_ARCHITECTURE.md)
- [Database Design](DATABASE_DESIGN.md)
- [API Summary](API_SUMMARY.md)

### Archive
The `archive/` directory contains historical documents, session summaries, implementation reports, and other ephemeral files. These are kept for reference but may be outdated.

## Documentation Guidelines

### When Creating Documentation

1. **Prefer updates over new files** - Check if existing documentation can be updated
2. **Use appropriate subdirectories** - Place files in the correct category
3. **Use kebab-case naming** - e.g., `edi-format-guide.md` not `EDIFORMATGUIDE.md`
4. **Avoid generic names** - Be specific (e.g., `pipeline-error-handling.md` not `summary.md`)
5. **No date stamps** - Unless specifically needed for versioning

### Ephemeral vs. Permanent

**Permanent (keep in docs/)**:
- User-facing guides
- API contracts
- Architecture decisions
- Format specifications
- Testing guides

**Ephemeral (archive or session-only)**:
- Session summaries
- Implementation plans
- Debug session notes
- Progress reports
- Temporary checklists

## Related Files

- **[README.md](../README.md)** - Project overview
- **[DOCUMENTATION.md](../DOCUMENTATION.md)** - Complete documentation with technical details
- **[AGENTS.md](../AGENTS.md)** - Agent-specific instructions
