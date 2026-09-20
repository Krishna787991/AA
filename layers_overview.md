# Data Layers Overview

## Big Data Platform

---

# Architecture Overview

## Data Flow

```text
Primary Systems
      │
      ▼
    Kafka
      │
      ▼
Kafka Connect Consumers
      │
      ▼
Landing Layer
      │
      ▼
File Compactor
      │
      ▼
Compacted Layer
      │
      ▼
Curated Loader
      │
      ▼
Curated Layer
      │
      ▼
Common Loader
      │
      ▼
Common Layer
      │
      ▼
Users / Applications
```

Additional components:

- Predictor Engine Storage (PES)
- User Schemas
- Spark
- Hive
- Impala
- Predictor Data
- User Transformed Data

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Data Sources

## Primary Systems

Data enters BDP through Apache Kafka.

### Characteristics

- Message-based architecture
- Producer/Consumer model
- Stream processing platform
- Typical retention period: 7 days
- Loaded using Confluent Kafka Connect
- Supports nested semi-structured data

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Kafka Topics

A Kafka topic represents a stream of related messages.

### Example

```text
gma.device.v3
```

| Part | Meaning |
|--------|---------|
| gma | Source system (Global Mobile Application) |
| device | Topic name |
| v3 | Topic version |

### Notes

- All events of a given category are stored in a topic.
- A topic may contain multiple message formats.

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Landing Layer

## Purpose

Raw storage layer for incoming Kafka data.

### Characteristics

- Parquet storage format
- Uses Confluent Kafka Connect
- One connector per topic
- Separate connector configuration
- Not accessible to end users
- Part of Medallion Architecture

### Responsibilities

- Add new connectors
- Modify connectors
- Decommission connectors
- Monitor 160+ connectors

### Retention

- 7-day retention

### Data Type

- Raw data

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Compacted Layer

## Purpose

Long-term storage of raw historical data.

### Application

```text
File Compactor
```

### Features

- Compacts landing layer files after 7 days
- Merges many small files into fewer large files
- Improves HDFS storage efficiency
- Stores compressed Parquet files
- Preserves historical raw data
- Not user accessible

### Benefits

- Faster storage operations
- Reduced file management overhead
- Supports full reloads after failures
- Avoids re-streaming from source systems

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Curated Layer

## Application

```text
Curated Loader
```

## Purpose

Creates Hive and Impala tables for business consumption.

### Capabilities

- Raw-to-curated transformation
- Hive-compatible table generation
- Query-ready datasets

### Transformations

- Unsupported Parquet types converted to String
- Audit columns added
- Schema evolution handling

### Unsupported Hive Types

- date
- boolean
- timestamp

### Original Goals

- Data cleansing
- De-duplication
- Re-partitioning

### Load Types

#### Daily Processing

- Incremental loads
- Fault tolerance
- Automatic source selection
  - Landing Layer
  - Compacted Layer

#### Historical Loading

- Full reload support
- Reprocessing with new transformations

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Curated Layer Additional Features

### Security

- IDM-role based access
- Managed through Grant Manager

### Monitoring

- Row count monitoring
- Reconciliation support

### Intraday Processing

Spark Streaming based processing.

Characteristics:

- Processes Landing Layer data
- 30-minute micro-batches
- Configurable intervals

### Note

Currently not used in India environment.

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Heartbeat Reconciliations

## Purpose

Data consistency verification mechanism.

### Functionality

- Compares received message counts
- Compares source-produced message counts
- Detects upstream failures
- Helps ensure data consistency

### Benefits

- Early problem identification
- Data quality assurance
- Monitoring support

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Common Layer

## Application

```text
Common Loader
```

## Purpose

Framework for creating managed data marts.

### Features

- SQL-based transformations
- Spark transformation support
- Monitoring included
- Alerting included
- Custom metrics
- DQ testing framework
- Unit testing framework

### Capabilities

- Incremental loads
- Native upserts
- Spark XML support
- Custom UDF support
- Modular ETLs

### Governance

- Access managed through Grant Manager
- Enforced conventions:
  - Naming standards
  - Data formats
  - Unified data management

### Usage

Currently used only by Common Data Mart.

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Predictors

## Purpose

Calculates and validates predictors.

### Outputs

Published only through Kafka.

### Consumers

- Predictor Engine Storage (PES)
  - UWI Stream
- Loxon
  - COLL Stream

### Status

Currently not used in India environment.

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Predictor Groups

## Silver Predictors

### Characteristics

- Validated and exported
- Calculated outside application
- Business-user driven
- Supports experimentation
- Faster development

## Gold Predictors

### Characteristics

- Calculated within Predictors application
- Fully managed
- Production-grade implementation

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Predictor Types and Groups

| Group | Type |
|---------|---------|
| COLL Silver | Collection |
| COLL Golden | Collection |
| CRM Silver | Underwriting |
| CRM Golden | Underwriting |
| UWI Silver | Underwriting |
| UWI Golden | Underwriting |

### Currently Active

- COLL Silver
- UWI Silver

### Predictor Storage

Stores calculated attributes from multiple sources for:

- Underwriting
- CRM
- Other business users

Uses:

- Kafka for ingestion
- REST APIs for access

Primary usage:

- Historical (D-1) underwriting predictors

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Monitoring

## Purpose

- Incident prevention
- Alerting
- Troubleshooting

### Sources

- Application metrics
- Application logs
- Spark logs

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Monitoring - Metrics

## Storage

### Prometheus

Two instances:

#### BDP

Used primarily by DevOps.

Captures:

- Infrastructure metrics
- Kafka Connect metrics

#### K8S

Used by Developers.

Captures:

- Application metrics

### Visualization

Grafana

- BDP Grafana
- K8S Grafana

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Monitoring Pipeline

```text
Application
     │
     ▼
metrics-exporter
     │
     ▼
VictoriaMetrics
     │
     ▼
Prometheus
(24h retention)
     │
     ▼
Thanos
(30d+ retention)
     │
     ▼
Grafana Dashboards

Prometheus
     │
     ▼
AlertManager
     │
     ▼
Email
MS Teams
PagerDuty
```

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Monitoring - Logs

## Log Storage

Logs stored as:

- Plain text
- JSON

Generated using:

```text
bdp-logger
```

Typical location:

```text
/var/log/apps/<app>/xxx.log
```

### Splunk

Responsibilities:

- Index logs
- Search logs
- Generate alerts

### Notifications

- Email alerts

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Typical Troubleshooting Example

Common errors found in logs:

- Spark configuration warnings
- Permission issues
- HDFS access violations
- Application failures

Example:

```text
AccessControlException:
Permission denied
user=app_file_compactor
access=READ_EXECUTE
```

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Layer Summary

## Landing Layer

- Raw Kafka data
- 7-day retention
- Parquet format

## Compacted Layer

- Historical raw data
- Optimized storage
- Long-term retention

## Curated Layer

- Hive/Impala ready data
- Business consumption

## Common Layer

- Data marts
- Business transformations

## Predictors

- Analytical outputs
- Kafka-based delivery

Source: 03. Data layers overview.pptx 【1-ba88be】

---

# Q&A

TODO:
- Continue with Setup Guide Part 1 (~30 minutes)

Source: 03. Data layers overview.pptx 【1-ba88be】
