# TODO - AAL-Core Project Tasks

## Completed ✓

### Branch Merges (2025-12-31)
- [x] Merge claude/add-yggdrasil-ir-B2h3o - YGGDRASIL-IR metadata layer
- [x] Merge claude/add-phase-policy-enforcement-zE1qq - Phase policy enforcement
- [x] Merge claude/beatoven-metrics-integration-kdAjo - BeatOven metrics integration
- [x] Merge claude/dynamic-function-discovery-hTidH - Dynamic function discovery
- [x] Merge claude/dynamic-function-registry-tiDmM - Function registry
- [x] Merge claude/oracle-runes-integration-modVV - Oracle-Runes integration
- [x] Merge claude/setup-aal-core-01T6F5YXgHtnV7iyxBaxUC1n - AAL-Core setup
- [x] Resolve all merge conflicts
- [x] Update README.md with merged features
- [x] Create Claude.md project documentation
- [x] Create TODO.md task tracker

### Project Roadmap & Stabilization (2026-01-12)
- [x] Create ROADMAP.md with project status and milestones
- [x] Assess test suite health (initially 297 tests, 11 import errors)
- [x] Fix render() function import in luma pipeline
- [x] Fix SvgStaticRenderer and SvgRenderConfig imports
- [x] Install project dependencies
- [x] Fix ALL import errors (11 → 0, 100% resolution)
- [x] Add missing effects_store functions (get_effect_mean, save_effects, load_effects, stderr, variance)
- [x] Add missing portfolio types (ImpactVector, PortfolioBudgets, etc.)
- [x] Add RunningStats.stderr() method
- [x] Migrate test_svg_hash.py to new SceneEntity/SceneEdge API
- [x] Add @dataclass decorator to SvgRenderConfig
- [x] Run full test suite: 315 tests collected, 279 passing (88.6%)
- [x] Update README.md with test metrics and current status
- [x] Update ROADMAP.md with test results and categorization
- [x] Update Claude.md with comprehensive handoff documentation

## High Priority

### Test Stabilization (IN PROGRESS - 88.6% Complete)
**Current Status:** 279/315 passing (88.6%), 31 failures, 5 skipped

**Remaining Failures (31 tests):**
- [ ] Portfolio & ERS (15 failures):
  - [ ] Fix effects store integration issues
  - [ ] Fix portfolio optimizer with baseline signatures
  - [ ] Fix canary rollback logic
- [ ] Overlay & Policy (4 failures):
  - [ ] Fix ascend permission tests
  - [ ] Fix canary deployment tests
- [ ] Rendering (2 failures):
  - [ ] Add RenderArtifact.from_text() factory method
  - [ ] Fix motif lattice placement
- [ ] Other subsystems (10 failures):
  - [ ] Triage and categorize remaining failures

**Next Steps:**
- [ ] Create test health dashboard or CI badge
- [ ] Set up automated test runs in CI/CD

## High Priority

### Core Infrastructure
- [ ] Add comprehensive integration tests for all merged subsystems
- [ ] Verify all imports and dependencies are correctly wired
- [ ] Run full test suite and fix any broken tests
- [ ] Set up CI/CD pipeline for automated testing
- [ ] Add type hints to all public APIs
- [ ] Generate API documentation from code

### Memory Governance
- [ ] Wire LLM/pipeline to respect job.metadata degradation parameters
- [ ] Add cgroup/container enforcement for hard_cap_mb limits
- [ ] Implement tier-specific memory allocators (LOCAL/EXTENDED/COLD)
- [ ] Add metrics collection for RAM_STRESS vs degradation effectiveness
- [ ] Tune degradation thresholds based on workload characteristics

### Overlay System
- [ ] Add overlay capability enforcement tests for all phases
- [ ] Implement hot-reload for overlay manifests
- [ ] Add overlay version compatibility checks
- [ ] Create overlay development template/scaffolding tool
- [ ] Add overlay performance monitoring and profiling

### YGGDRASIL-IR
- [ ] Complete documentation for bridge promotion workflow
- [ ] Add evidence bundle validation and verification tools
- [ ] Implement automated evidence relock scheduling
- [ ] Add bridge health monitoring and alerting
- [ ] Create example evidence bundles for all overlay types

### Function Registry
- [ ] Add support for function versioning and deprecation
- [ ] Implement function dependency graph visualization
- [ ] Add rate limiting and throttling for remote function discovery
- [ ] Create function catalog export/import tools
- [ ] Add function usage analytics and metrics

## Medium Priority

### Policy & Governance
- [ ] Add policy versioning and rollback capability
- [ ] Implement policy dry-run mode for testing
- [ ] Create policy migration tools for upgrades
- [ ] Add policy violation analytics dashboard
- [ ] Document policy best practices and patterns

### Provenance & Replay
- [ ] Add partial replay with state snapshots
- [ ] Implement provenance query and search API
- [ ] Create provenance visualization tools
- [ ] Add provenance export to standard formats (Parquet, Arrow)
- [ ] Implement distributed provenance aggregation

### Oracle & Runes
- [ ] Add more rune operators (FILTER, TRANSFORM, VALIDATE)
- [ ] Implement rune composition and chaining
- [ ] Create rune development guide and examples
- [ ] Add rune performance benchmarks
- [ ] Implement rune caching and memoization

### Alignment System
- [ ] Test alignment governor with real workloads
- [ ] Add regime transition analytics and logging
- [ ] Implement capability graph pruning and optimization
- [ ] Create alignment system stress tests
- [ ] Add objective firewall rule library

## Low Priority

### Developer Experience
- [ ] Add development environment setup script
- [ ] Create VS Code workspace configuration
- [ ] Add debugging helpers and utilities
- [ ] Create developer onboarding guide
- [ ] Add code quality tooling (linters, formatters)

### Documentation
- [ ] Create architecture decision records (ADRs)
- [ ] Add sequence diagrams for key workflows
- [ ] Create video tutorials for common tasks
- [ ] Add API reference documentation
- [ ] Create troubleshooting guide

### Performance
- [ ] Profile overlay invocation latency
- [ ] Optimize manifest loading and caching
- [ ] Add connection pooling for remote services
- [ ] Implement async overlay execution
- [ ] Add performance benchmarking suite

### Deployment
- [ ] Create Docker container images
- [ ] Add Kubernetes deployment manifests
- [ ] Create Terraform/IaC templates
- [ ] Add health check and readiness probes
- [ ] Implement graceful shutdown handling

## Future Enhancements

### Advanced Features
- [ ] Distributed overlay execution across multiple nodes
- [ ] Cross-overlay data flow tracking and provenance
- [ ] Real-time overlay collaboration and state sharing
- [ ] Dynamic overlay composition and workflow building
- [ ] Machine learning-based overlay recommendation

### Integration
- [ ] Add Prometheus metrics exporter
- [ ] Implement OpenTelemetry tracing
- [ ] Add Grafana dashboard templates
- [ ] Create Slack/Discord notification integrations
- [ ] Add webhook support for external events

### Security
- [ ] Implement overlay code signing and verification
- [ ] Add encrypted provenance logging option
- [ ] Implement fine-grained RBAC for overlay execution
- [ ] Add audit logging for security events
- [ ] Create security scanning and vulnerability detection

## Notes

- All high-priority tasks should be completed before next major release
- Medium-priority tasks are good candidates for community contributions
- Future enhancements require architectural design discussions
- Keep this TODO.md updated as tasks are completed or priorities change
