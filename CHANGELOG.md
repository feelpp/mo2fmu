# Changelog

All notable changes to `mo2fmu` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- No unreleased changes yet.

## [1.0.0] - 2026-03-23

### Added
- Added FMI 3.0 generation support for both Dymola and OpenModelica backends.
- Added camelCase public Python APIs: `checkCompilers()`, `getCompiler()`, and `compileFmu()`.
- Added the `mo2fmu compile` and `mo2fmu check` CLI subcommands.
- Added backward-compatible legacy wrappers that emit deprecation warnings.
- Added broader test coverage for FMI 2.0 and FMI 3.0, including co-simulation and model-exchange workflows.
- Added the batch compilation API `compileFmus()` and the `CompilationRequest` data model.
- Added Dymola batch compilation support that reuses a single session across multiple FMU builds.
- Added Dymola startup retry configuration for transient floating-license exhaustion.

### Changed
- Refactored the public API and CLI around the new camelCase naming scheme.
- Improved backend abstraction and configuration handling for Dymola and OpenModelica.
- Updated project documentation and packaging metadata for the 1.0 release line.
- Updated release and versioning documentation to reflect the tag-driven GitHub Actions workflow.

### Fixed
- Suppressed OMPython `pyparsing` deprecation warnings at import time so pytest runs cleanly when warnings are treated as errors.
- Updated Dymola integration tests to skip cleanly when no shareable compile license is available instead of failing on CI environment constraints.
- Tightened type checking, formatting, and test helpers introduced during the Dymola session-management work.

## [0.6.0] - 2025-11-02

### Added

#### Documentation
- **Comprehensive Antora Documentation**: Complete rewrite of documentation with extensive coverage
  - New home page with clear feature highlights and navigation
  - Enhanced overview with technical details and architecture
  - Improved quickstart guide with installation and first conversion
  - Complete CLI usage guide with all options and examples
  - Detailed Python API documentation with 10+ code examples
  - Configuration guide for all platforms (Linux, macOS, Windows)
  - 20 practical examples covering basic to advanced usage scenarios
  - Troubleshooting guide with common issues and solutions
  - FAQ page with frequently asked questions
  - New navigation structure for better usability

#### Documentation Pages
- `usage-cli.adoc` - Command-line interface complete reference
- `usage-python.adoc` - Python API with extensive examples
- `configuration.adoc` - Environment setup and Dymola configuration
- `examples.adoc` - 20 real-world usage examples
- `troubleshooting.adoc` - Debugging and problem resolution
- `faq.adoc` - Common questions and answers

### Changed
- Updated `index.adoc` with modern landing page
- Enhanced `overview.adoc` with project architecture details
- Improved `quickstart.adoc` with step-by-step guide
- Reorganized `nav.adoc` with logical section grouping

### Documentation Coverage
- Getting started and installation
- CLI reference with all options
- Python API with function signatures
- Configuration for all platforms
- FMI types (CS, ME, all, csSolver)
- Package loading and dependencies
- Custom Dymola flags
- Batch processing examples
- CI/CD integration examples
- Error handling and debugging
- Performance optimization tips
- Cross-platform usage

## [0.5.2] - 2025-10-29

### Current Features
- Modelica to FMU conversion using Dymola
- Command-line interface (CLI) tool
- Python API for programmatic access
- Support for FMI 2.0 standard
- Multiple FMI types: CS, ME, all, csSolver
- Package loading support
- Custom Dymola flags
- 64-bit FMU generation
- Code export enabled (license-free execution)
- Full compiler optimizations
- Virtual framebuffer (Xvfb) for headless operation
- Environment-based configuration
- Verbose logging mode
- Force overwrite option

## [0.5.1] - Previous Release

Previous versions available on PyPI.

---

## Release Notes

### Version 0.6.0 - Documentation Release

This release focuses on comprehensive documentation to help users get started with mo2fmu and use it effectively.

**Highlights:**
- Complete documentation rewrite with Antora
- 10 new documentation pages covering all aspects
- 20 practical examples from basic to advanced
- Troubleshooting guide for common issues
- FAQ with quick answers
- Better navigation and organization

**Target Users:**
- New users learning mo2fmu
- Developers integrating mo2fmu into workflows
- CI/CD pipeline maintainers
- Python developers using the API
- Users troubleshooting issues

**Documentation Accessibility:**
- Online: https://feelpp.github.io/mo2fmu
- Source: `docs/modules/ROOT/pages/`
- Format: AsciiDoc with Antora

---

## Migration Guide

### From 0.5.x to 0.6.0

No breaking changes. This is a documentation-focused release.

**What's New:**
- Enhanced documentation available online and in repository
- Better examples for common use cases
- Improved troubleshooting resources

**Action Required:**
- None - fully backward compatible
- Recommended: Review new documentation for best practices

---

## Future Releases

### Planned Features
- FMI 3.0 support
- Additional Dymola version compatibility
- Enhanced error reporting
- Performance improvements
- More configuration options

### Community Contributions
We welcome contributions! See:
- Documentation improvements
- Bug fixes
- New examples
- Feature requests

Repository: https://github.com/feelpp/mo2fmu
Issues: https://github.com/feelpp/mo2fmu/issues

---

## Links

- **PyPI**: https://pypi.org/project/feelpp-mo2fmu/
- **Documentation**: https://feelpp.github.io/mo2fmu
- **Repository**: https://github.com/feelpp/mo2fmu
- **Issues**: https://github.com/feelpp/mo2fmu/issues
- **Feel++ Website**: https://feelpp.org
