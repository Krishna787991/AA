# BDP Cluster Overview

## Big Data Platform

---

## BDP Benefits

- Scalability through horizontal scaling
- High Availability (HA) and Fault Tolerance using HDFS
- Distributed Processing
- Unified Data Platform:
  - Storage
  - Compute
  - Security
  - Governance
- Integration between tools:
  - Spark
  - Kafka
  - Splunk
- Enterprise support and administration through Cloudera Manager

---

## External Services Used by BDP

- CyberArk
- Kubernetes
- Splunk
- Thanos
- Prometheus
- Grafana
- SonarQube
- GitLab
- Nexus
- Jira
- Harbor

---

# Cloudera

Cloudera is a data platform that provides tools and infrastructure for storing, processing, analyzing, and managing large volumes of data using distributed open-source technologies.

### Core Technologies

- Apache Hadoop (HDFS, YARN)
- Apache Hive
- Apache Impala
- Apache Spark
- Apache HBase

---

## Cloudera Environment

### Version
- CDH 6.3.2

### Limitations

- No longer supported
- No fixes or security patches
- Uses Sentry
- No metadata governance
- Manual LDAP/Kerberos setup
- Several custom implementations

### Advantages

- Single cluster High Availability
- Jupyter support with pluggable kernels
- Multiple Spark versions
- OS and AD integrations

---

# Core Cloudera Services

## HDFS

Distributed file system for reliable storage of big data.

### Characteristics

- Optimized for large sequential reads and writes
- Horizontal scalability
- Petabyte-scale storage
- Default replication factor: 3
- High Availability support
- Data integrity validation through checksums

### Key Concepts

- Active and Passive NameNode
- Erasure Coding
- Data Replication
- Block Size
- Heartbeats
- Replica Reads
- Safe Mode

### Metadata

- editlog
- fsimage

### Failure Handling

- Network partitions
- DataNode failures
- NameNode failures

### Design Principles

- Hardware failure is expected
- Streaming data access
- Large datasets
- Simple coherency model
- Moving computation is cheaper than moving data
- Platform portability

---

## YARN (Yet Another Resource Negotiator)

Resource management and scheduling framework for Hadoop.

### Responsibilities

- Resource management
- Job scheduling
- Job monitoring
- Compute resource allocation

### Components

#### ResourceManager
- Cluster-wide resource allocation
- Scheduler
- Application management

#### ApplicationMaster
- Controls lifecycle of jobs

#### NodeManager
- Manages resources on a node
- Monitors:
  - CPU
  - Memory
  - Disk
  - Network

#### Scheduler
- Assigns:
  - CPU
  - Memory
  - Disk
  - Network resources

### Additional Concepts

- Containers
  - Aggregation of CPU, memory and storage resources

---

## Hive

SQL-based ETL framework over Hadoop.

### Purpose

- SQL-like interface to HDFS
- HiveQL support
- Converts queries into:
  - MapReduce
  - Tez
  - Spark jobs

### Components

- Metastore
- Driver
- Compiler
- Optimizer
- Executor
- CLI
- UI
- Thrift Server

### Architecture

#### Metastore
Stores:
- Tables
- Partitions
- Schemas
- HDFS locations

#### Driver
- Session management
- Query execution

#### Compiler
- Parsing
- Semantic analysis
- Execution plan generation

#### Execution Engine
- Executes DAG execution plans

---

## Impala

Massively Parallel Processing (MPP) SQL engine.

### Features

- High-performance SQL
- Low latency
- Hadoop integration
- Security support

### Components

#### Impala Daemon (impalad)

- Reads/Writes data files
- Executes queries
- Distributes work
- Returns results

#### StateStore

- Monitors daemon health
- Shares cluster state

#### Catalog Service

- Synchronizes metadata changes

---

## Spark

Open-source distributed data processing framework.

### Features

- In-memory processing
- Unified analytics
- Polyglot programming
- Fault tolerance
- Lazy evaluation
- DAG execution engine

### Architecture

#### Driver Program

- Central coordinator
- Holds SparkContext
- Creates execution plans
- Schedules tasks

#### Cluster Manager

Options:

- Standalone
- YARN
- Apache Mesos
- Kubernetes

#### Executors

- Execute tasks
- Store cached data
- Handle shuffles

#### Worker Nodes

- Host executors
- Execute distributed workloads

### Important Concepts

- RDD
- Lineage
- Caching
- DAG
- Stages
- Tasks

---

# Cloudera Manager

## Components

### Agent

Installed on every host.

Responsibilities:
- Start services
- Stop services
- Deploy configurations
- Monitoring

### Management Service

Provides:
- Monitoring
- Alerting
- Reporting

### Database

Stores:
- Cluster configuration
- Monitoring metrics

### Cloudera Repository

Software distribution repository.

### Clients

#### Admin Console

Web UI for cluster administration.

#### API

Programmatic cluster access.

---

## Cloudera Management Service

### Responsibilities

- Service configuration
- Cluster configuration updates
- Parcel management
- Monitoring
- Logging
- Diagnostics

---

## Management Components

### Alert Publisher

- Generates alerts
- Delivers notifications

### Event Server

- Aggregates Hadoop events

### Host Monitor

- Collects host metrics

### Service Monitor

- Monitors YARN
- Monitors Impala
- Monitors service health

---

# HBase

### Status

Not used by BDP.

### Purpose

- Distributed NoSQL data store
- Real-time read/write access
- Typically used as a serving layer

### Notes

- Complex configuration
- Steep learning curve

---

# Cloudera Service Roles

## HDFS

- DataNode
- Gateway
- HttpFS
- JournalNode
- NameNode
- Custom HDFS Monitoring

---

## Hive

- Hive Gateway
- Hive Metastore Server
- HiveServer2

---

## Hue

### Purpose

Web-based Hadoop user interface.

Provides:
- Query execution
- Data browsing
- Job management

---

## Impala

- Catalog Server
- Impala Daemon
- StateStore
- Custom Impala Refresher service

---

## Additional Services

- Oozie Server
- Sentry Gateway
- Sentry Server
- Spark Gateway
- Spark History Server
- Jupyter Gateway
- Jupyter Hub
- Kudu Master
- Kudu Tablet Server
- Livy Gateway
- Livy REST Server
- ZooKeeper Server

---

## YARN Services

- YARN Gateway
- JobHistory Server
- NodeManager
- ResourceManager

---

# Cluster Architecture

## Edge Node

### Purpose

Main client-facing node.

### Responsibilities

- Client configurations
- Jupyter Hub
- Application deployment
- Enhanced memory for Jupyter

### Key Locations

```text
/opt/bdp/apps/
/var/log/apps/
```

---

## Utility Node

### Services

- Cloudera Manager
- Management Services
- Spark Job History Server
- HDFS HttpFS

---

## Head Nodes

### Services

- Hue Server
- Impala Catalog Server
- ZooKeeper Server

### Purpose

Cluster management and orchestration.

---

## Worker Nodes

### Responsibilities

- Data storage
- Distributed processing

### Services

- Hue Server
- Kudu Tablet Server
- YARN NodeManager
- HDFS DataNode
- Impala Daemon
- Kafka Connect Containers

---

# Environments

- UAT
- PROD

---

# Environment Documentation

## Wiki

https://wiki.homecredit.net/confluence/display/DWH/IN+BDP

### Main Areas

- Dashboard Structure
- Main Links
- YARN
- HBase
- Spark
- Impala
- Kudu
- Prometheus
- Grafana
- Netdata

---

# Edge Node Folders

## SSH Access

Technical Account Home Folder

## Deployment Root

```text
/opt/bdp/apps/
```

## Logs Root

```text
/var/log/apps/
```

---

# Technical Account Applications

- app_coll_monitoring
- app_common_loader
- app_curated_loader
- app_file_compactor
- app_landing_loader
- app_predictors
- app_reconciliation
- app_table_compactor
- app_batch_importer

---

# Hardware Overview

## Compute

- CPU: 384 Intel Xeon Platinum 8462Y+ cores
- Memory: 1832.6 GiB

## Storage

- Total Storage: 527.9 TiB
- HDFS Storage: 495.7 TiB

---

# YARN Capacity

Cluster resources are divided into queues for workload isolation and resource management.

---

## Default Queue

### Reserved Resources

- CPU: 54 vCores
- Memory: 108 GiB

### Settings

- Preemption Disabled

---

## Application Queue

### Reserved Resources

- CPU: 144 vCores
- Memory: 288 GiB

### Maximum Resources

- CPU: 288 vCores
- Memory: 576 GiB

---

## Analyst Queue

### Reserved Resources

- CPU: 144 vCores
- Memory: 288 GiB

### Maximum Resources

- CPU: 216 vCores
- Memory: 432 GiB

---

# Q&A
