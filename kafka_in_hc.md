# Kafka in HC

---

# Learning Objectives

By the end of this session, you will understand:

- What Kafka is
- What a Kafka topic is
- How Kafka messages are structured
- How Kafka Connect works
- How data flows between:
  - Primary Systems
  - Kafka
  - HDFS

---

# Kafka Basics

## What is Kafka?

Kafka is a platform that enables systems to exchange data as messages in real time.

### Core Concepts

#### Topics

Kafka organizes data into categories called **Topics**.

Examples:

```text
Topic A
Topic B
Topic C
```

#### Producers

Applications that publish messages into Kafka topics.

```text
Application → Kafka Topic
```

#### Consumers

Applications that read messages from Kafka topics.

```text
Kafka Topic → Application
```

### Publish / Subscribe Model

```text
Producer
    ↓ Publish

Kafka Topic

    ↓ Subscribe
Consumer
```

### Consumer Groups

Important rule:

- Only one consumer within the same consumer group receives a specific message.

---

# Kafka Topics

A Kafka topic consists of one or more partitions.

## Partition Example

```text
Partition 0: 0 1 2 3 4 ...
Partition 1: 0 1 2 3 4 ...
Partition 2: 0 1 2 3 4 ...
```

### Offsets

Each message receives a unique offset within its partition.

```text
Offset = Position of message inside a partition
```

### Characteristics

- Messages inside a partition are ordered
- Topics contain one or more partitions
- New messages are always appended

### Benefits

#### Parallelism

Multiple consumers can process partitions in parallel.

#### Scalability

More partitions provide higher throughput.

#### Resilience

Partitions can be replicated.

### Best Practice

```text
Number of consumers ≈ Number of partitions
```

---

# Kafka Connect Basics

## What is Kafka Connect?

Kafka Connect is a framework that integrates Kafka with external systems through connectors.

### Connector Types

#### Source Connectors

Pull data from external systems into Kafka.

```text
External System
      ↓
Source Connector
      ↓
Kafka
```

#### Sink Connectors

Push data from Kafka into external systems.

```text
Kafka
     ↓
Sink Connector
     ↓
External System
```

---

# Data Flow: Primary Systems to HDFS

## High-Level Architecture

```text
Primary System
      ↓
Kafka Connect Source Connector
      ↓
Kafka Topic
      ↓
Kafka Connect Sink Connector
      ↓
Landing Layer
      ↓
Compacted Layer
      ↓
Curated Layer
```

### Environment Statistics

- Approximately 400 Kafka topics exist
- Around 170 topics are consumed into HDFS

### Consumption Strategy

Topic consumption depends on business requirements.

### Topic Naming Examples

```text
am.event-info.v1
csd.boundary.v1
gma.device.v3
lcs.streaming.actor.v1
pif.applicantperson.v4
```

Typically:

```text
<source_system>.<topic_name>.<version>
```

### Documentation

Consumed stream list:

```text
https://docs.cz.infra/bigdata/Hadoop_consumed-data-streams.html
```

---

# Data Flow: Primary Systems to Kafka

Most systems do not publish directly to Kafka.

## Actual Process

```text
Application
      ↓
Database Table
      ↓
Kafka Connect
      ↓
Kafka Topic
```

### Why?

Applications write events into dedicated database tables.

Kafka Connect continuously polls those tables and publishes events into Kafka.

---

# Outbox Pattern

## Standard Integration Pattern

```text
Application
      ↓
Outbox Table
      ↓
JDBC Source Connector
      ↓
Kafka Topic
```

### Example

```text
ADS.V_ADS_EVENT_SOURCE
```

produces

```text
ads.application-data.v2
```

through

```text
ADS JDBC Source Connector
```

### Benefits

#### Transaction Safety

Events are written within the same database transaction.

#### Reliability

Kafka Connect keeps retrying until successful.

#### Auditability

All sent events remain stored in the outbox table.

---

# JDBC Source Connector Configuration

Each connector configuration defines:

- Database connection
- Source outbox table
- New-event detection strategy
- Destination Kafka topic
- Polling frequency
- Preprocessing logic
- Message format

### Repository

```text
https://git.homecredit.net/customers/hcin/hosel/confluent-kafka/kafka-connect/-/tree/master/templates
```

---

# Reconciliations

## Purpose

Verify that the number of events sent equals the number received.

### Standard Topics

Business Topic:

```text
ads.application-data.v2
```

Reconciliation Topic:

```text
tech.reconciliation.v1
```

### Flow

```text
Outbox Table
      ↓
Business Connector
      ↓
Business Topic

Outbox Table
      ↓
Reconciliation Connector
      ↓
tech.reconciliation.v1
```

### Reconciliation Message Contains

- Source Kafka topic
- Reconciliation date
- Message count

### Validation

The Reconciliation application compares:

```text
Messages produced
vs
Messages received in Curated Layer
```

This helps detect:

- Missing events
- Processing failures
- Data consistency issues

---

# Kafka Topic Configuration

Topics are managed through Git.

### Repository

```text
https://git.homecredit.net/customers/hcin/hosel/confluent-kafka/kafka-configurations
```

---

## Key Configuration Parameters

### Number of Partitions

Determined primarily by expected traffic volume.

### Retention Period

Requirement for Hadoop-consumed topics:

```text
Minimum 7 days retention
```

Purpose:

- Data recovery
- Failure handling
- Reprocessing support

### ACL Configuration

Access permissions are managed in the same repository.

---

## BDP Kafka User

User:

```text
EIT_BDP_User
```

Permissions:

### Read

```text
All Topics
```

### Write

```text
Predictor Topics Only
```

Used by:

```text
Predictors Application
```

---

## AKHQ

AKHQ is used to inspect Kafka topics.

Capabilities:

- View topic details
- View partitions
- View retention settings
- Browse messages
- Review topic configuration

---

# Kafka Message Structure

A Kafka message has three main components:

```text
Key
Headers
Payload
```

---

## Key

### Purpose

Used for partition assignment.

### Typical Usage

#### Even Distribution

```text
null
```

or

```text
Random UUID
```

#### Ordered Processing

Use deterministic keys.

Examples:

```text
customer_id
contract_id
device_id
```

This ensures related messages land in the same partition.

---

## Headers

Metadata attached to the message.

### Characteristics

- Key-value pairs
- Separate from payload
- Must follow company conventions
- Useful for filtering
- Useful for auditing

---

## Payload

The actual business data.

### Format

Usually:

```text
AVRO Binary Format
```

### Additional Information

Every message contains:

```text
Schema ID
```

which identifies the schema needed to decode it.

---

# Schema Registry

## Purpose

Stores AVRO schemas used by Kafka messages.

### Schema Defines

- Field names
- Data types
- Mandatory fields
- Optional fields
- Default values

### Process

```text
Kafka Message
      ↓
Schema ID
      ↓
Schema Registry
      ↓
Schema Retrieval
      ↓
Payload Deserialization
```

### Benefits

- Validation
- Compatibility checks
- Standardized message structures

---

# Schema Evolution

Kafka supports schema evolution.

## Major Changes

Examples:

- Breaking changes
- Non-forward-compatible changes

### Requirement

Create a new topic.

```text
New Schema
    ↓
New Topic
```

---

## Minor Changes

Examples:

- Adding optional fields
- Forward-compatible updates

### Process

- Producer updates schema
- Schema Registry stores new version
- Consumers automatically use newest compatible schema

### Result

No new topic required.

---

# Key Takeaways

- Kafka enables real-time data exchange.
- Topics are divided into partitions for scale and resilience.
- Producers publish messages and consumers read them.
- Kafka Connect integrates databases and external systems.
- Most HC applications use the Outbox Pattern.
- HDFS ingestion is performed through Kafka Connect sink connectors.
- Kafka messages consist of:
  - Key
  - Headers
  - Payload
- AVRO schemas are managed through Schema Registry.
- Reconciliations ensure message count consistency across systems.

---

# Useful Links

## Kafka Connect Repository

```text
https://git.homecredit.net/customers/hcin/hosel/confluent-kafka/kafka-connect
```

## Kafka Configuration Repository

```text
https://git.homecredit.net/customers/hcin/hosel/confluent-kafka/kafka-configurations
```

## Consumed Data Streams

```text
https://docs.cz.infra/bigdata/Hadoop_consumed-data-streams.html
```

## AVRO Schema Conventions

```text
https://git.homecredit.net/product/arch-crew/reference-architecture/-/blob/master/010-avro-schema-management.md
```
