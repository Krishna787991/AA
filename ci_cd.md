# CI/CD Pipelines & Automation

## Big Data Platform

---

# Agenda

- Git & GitLab
  - Projects
  - Structure
  - Governance
- GitLab CI
  - Basics
  - Templates
  - Runners
- Runner Images
  - Build process
  - Harbor
  - Docker basics
- Build Jobs
  - SBT
  - Conda
  - Nexus
  - Conda-Forge
- Test Jobs
  - PyTest
  - ScalaTest
  - Unit Tests
  - Integration Tests
- Deployment Jobs
  - Nexus Deployment
  - Deployment Scripts

---

# Git Structure

## Repositories

### Big Data Git Groups

```text
https://git-eit.homecredit.in/bigdata
https://git.homecredit.net/groups/bigdata
https://git.homecredit.net/customers/hcin/data/bigdata
```

### Principles

- Projects organized into Git groups
- Common governance model
- Repository synchronization between environments
- Standardized project structure

---

# GitLab

## Overview

GitLab is a web-based platform built around Git.

### Features

- Version Control System (VCS)
- Built-in CI/CD
- Group hierarchy support
- Access control
- Markdown support
- Merge Request workflows

### Example Repositories

```text
https://git.homecredit.id/bigdata/app/curated-layer/curated-layer

https://git.homecredit.id/bigdata/app/utils/ci_templates

https://git.homecredit.id/bigdata/app/utils/ci_templates/-/blob/master/ci/env/id.yml
```

### Merge Request Example

```text
https://git.homecredit.net/bigdata/app/monitoring/splunk-alerts/-/merge_requests/36
```

---

# Development Lifecycle

## Recommended Workflow

### 1. Understand the Task

Before coding:

- Review requirements
- Ensure ticket contains all necessary information

### 2. Create Feature Branch

Naming convention:

```text
<ticket_number>-<feature_name>
```

### 3. Development

- Implement code
- Create tests
- Commit regularly

### 4. Create Merge Request Early

Benefits:

- Early feedback
- Visibility
- UAT testing support

### 5. Deploy to UAT

- Validate functionality
- Run tests

### 6. Review & Approval

- Peer review
- Fix comments

### 7. Merge to Master

After approvals:

```text
Feature Branch
      ↓
Merge Request
      ↓
UAT Validation
      ↓
Approval
      ↓
Master
```

### 8. Production Deployment

Deploy approved version to production.

---

# Unit and Integration Testing

## Testing Frameworks

### Unit Testing

- ScalaTest
- PyTest

### Quality Tools

- Coverage Reports
- SonarQube
- IntelliJ IDEA Plugin

### Integration Testing

- UAT-based testing
- Daily scheduled executions
- Non-production validation runs

---

# Unit Tests - Advantages

## Benefits

- Foundation of testing strategy
- Fast execution
- Easier troubleshooting
- Enables safe refactoring
- Prevents regressions
- Encourages good software design
- Useful in local development
- Useful in CI pipelines

### Typical Flow

```text
Local Development
       ↓
Unit Tests
       ↓
CI Validation
```

---

# Unit Tests - Challenges

## Common Problems

- Low adoption in data teams
- Additional development effort
- Difficult to introduce later
- Requires testing culture
- Requires strong methodology
- Spark testing can be complex

### However

Good unit testing still improves:

- Architecture
- Design quality
- Maintainability

---

# CI Pipelines - Benefits

## Why CI Matters

### Governance

- Enforced conventions
- Standardized implementation

### Collaboration

- Increased visibility
- Team sharing

### Quality

- Static code analysis
- Early bug detection

### Operations

- Shared runtime setup
- Auditability
- Repeatability

---

# CI Pipelines

## Trade-Offs

### Advantages

- Very reusable
- Consistent implementation
- Standardized workflows

### Challenges

- Initial setup investment
- Pipeline maintenance

### Key Principle

```text
One reusable template
>
Many custom implementations
```

Avoid duplicated CI configurations whenever possible.

---

# Integration Tests

## Benefits

### Realistic Testing

- End-to-end validation
- Real infrastructure
- Real integrations

### Automation

- Trigger from CI
- Nightly execution possible

### Coverage

- Complex scenarios
- Cross-system validations

---

## Challenges

- Slow execution
- Difficult debugging
- Hard setup
- Requires synthetic data
- Requires strong scenario design

### Current Status

Only implemented in selected projects.

---

# UAT Full Runs

## Characteristics

- Executed nightly
- Uses production-like jobs
- Strong predictor of production failures

### Advantages

- Easy setup
- Production simulation
- Early issue detection

### Challenges

- Data acquisition
- Environment consistency

### Important Guideline

Keep UAT and PROD aligned.

Especially:

- Cluster configuration
- Data structures
- Producer data delivery

---

# Scala Deployment Pipeline

## Deployment Target

```text
Code → Nexus
```

### Build Stage

Tool:

```text
SBT
```

Executed in:

```text
Kubernetes
```

Build image:

```text
bdp-base
```

### Dependencies

- Nexus Artifacts
- Internal Libraries
  - Logging
  - Monitoring
  - Spark Utilities

### Repository Sources

- Internal Nexus
- Maven Central Mirror
- Confluent Repository Mirror

---

## Test Stage

### Framework

```text
sbt test
```

### Coverage

```text
scoverage
```

### Static Analysis

```text
SonarQube
```

---

## Versioning

### Master Branch

Uses:

```text
Git Tag
```

### Feature Branches

Uses:

```text
GitLab Pipeline ID
```

---

## Artifact Upload

Final step:

```text
Upload Artifacts → Nexus
```

---

# Deployment Pipeline

## Nexus to Edge Deployment

### Execution

- Manual trigger
- GitLab Shell Runner

### Process

1. Checkout target version
2. Execute deployment scripts
3. Run under technical account
4. Deploy application

---

## Evolution

### Before

```text
Bash Scripts
+
Cron Jobs
```

### Current State

```text
appdeploy
+
Cron Jobs
```

### Future State

```text
appdeploy
+
Airflow
```

---

# Deployment Framework

## Custom Platform Components

### Configuration

Unified configuration using:

```text
HOCON
```

### Logging

Capabilities:

- Distributed logging
- Structured logging
- Splunk integration

---

## Metrics

Integrated with:

- Prometheus
- Thanos
- Grafana

---

## Spark Runtime

Provides:

- Standard Spark setup
- Defaults
- Runtime configuration

---

## Application Lifecycle

Features:

- Graceful shutdown
- Event listeners
- Default metrics collection

---

## Deployment Tooling

Benefits:

- Reduced Bash scripting
- Standardized deployments
- Less duplicated code
- Centralized deployment logic

---

# CI/CD Flow Summary

```text
Develop
   ↓
Unit Tests
   ↓
CI Pipeline
   ↓
Integration Tests
   ↓
UAT Run
   ↓
Build Artifact
   ↓
Nexus
   ↓
Deployment
   ↓
PROD
```

---

# Key Takeaways

- GitLab is the central development platform.
- CI pipelines enforce standards and quality.
- Unit tests are the foundation of reliable development.
- Integration tests validate real-world scenarios.
- Nexus serves as the artifact repository.
- Deployments are standardized through `appdeploy`.
- Monitoring and logging are integrated with:
  - Splunk
  - Prometheus
  - Thanos
  - Grafana
- The long-term direction is greater automation through Airflow.

---

# Q&A
