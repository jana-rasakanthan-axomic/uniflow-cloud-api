# EP01-T13-api: Cloud Status Vocabulary & Privacy Controls

**Epic:** EP-01 Platform Foundation
**Points:** 1
**Split From:** EP01-T13
**Primary Endpoint:** N/A (shared library + middleware)
**Depends On:** None

## Summary

Python enum library for status vocabulary with identical values to TypeScript edge/portal counterparts. PII-scrubbing log filter for cloud-side logging. TLS enforcement middleware. RDS and S3 encryption configuration.

## Context

Cross-app consistency prevents user confusion when Contributors and Curators discuss upload progress (BR-19, BR-20). Privacy controls (BR-02, BR-03, BR-04) ensure enterprise compliance.

**Technical Design Reference:** See docs/design/platform-foundation.md Section 4.2

## Acceptance Criteria

- [ ] Python enums with identical string values to TypeScript counterparts (job states, file states, device status)
- [ ] Color semantic constants: BLUE (active), GREEN (complete), AMBER (waiting), PURPLE (user-paused), RED (failed), GRAY (offline)
- [ ] Explanation template function: takes a state, returns human-readable text with next action
- [ ] PII-scrubbing log filter: strips email addresses, credentials, file paths using allowlist approach
- [ ] TLS enforcement middleware: rejects non-HTTPS requests via X-Forwarded-Proto header, requires TLS 1.2+
- [ ] RDS encryption at rest enabled (AES-256)
- [ ] S3 SSE enabled for thumbnail storage (AES-256)

## Business Rules

- BR-02: No Automatic Telemetry
- BR-03: No PII in Logs
- BR-04: Encryption Requirements
- BR-19: Unified Status Vocabulary
- BR-20: Shared Color Semantics
- BR-21: Human Status Explanations

## BDD Scenarios

- Cloud-side logs exclude file paths
- Local logs exclude personally identifiable information
- All agent-to-cloud communication uses TLS
- Cloud database uses encryption at rest
- Thumbnails use encryption at rest

## Technical Notes

Use Python enums with identical string values to TypeScript enums. PII scrubber uses allowlist approach (only allow known-safe patterns). TLS enforcement via FastAPI middleware checking X-Forwarded-Proto header. Use `logging.handlers.RotatingFileHandler` for structured logging.

## References

| Artifact | Type | Notes |
|----------|------|-------|
| docs/design/platform-foundation.md | tdd | Section 4.1 Data Privacy, Section 4.2 Status Vocabulary |
| .claude/active/ep01-platform-foundation/design/platform-foundation-rules.md | rules | BR-02, BR-03, BR-04, BR-19, BR-20, BR-21 |
| .claude/active/ep01-platform-foundation/design/platform-foundation-bdd.feature | bdd | Category 1 & 6 scenarios |
