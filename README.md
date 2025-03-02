# TradeStat Engine

## Overview

A high-performance RESTful service capable of handling the rigorous demands of high-frequency trading systems. This service will act as a component in the company ABC trading infrastructure, managing and analysing financial data in near real-time.


## Functional Requirements

Your service must support two HTTP-based API endpoints communicating via JSON:

### POST /add_batch/

**Purpose:** Allows the bulk addition of consecutive trading data points for a specific symbol. (in-memory storage)

**Input:**
- `symbol`: String identifier for the financial instrument.
- `values`: Array of up to 10000 floating-point numbers representing sequential trading prices ordered from oldest to newest.

**Response:** Confirmation of the batch data addition.

### GET /stats/

**Purpose:** To provide rapid statistical analyses of recent trading data for specified symbols.

**Input:**
- `symbol`: The financial instrument's identifier.
- `k`: An integer from 1 to 8, specifying the number of last 1e{k} data points to analyze.

**Response:**
- `min`: Minimum price in the last 1e{k} points.
- `max`: Maximum price in the last 1e{k} points.
- `last`: Most recent trading price.
- `avg`: Average price over the last 1e{k} points.
- `var`: Variance of prices over the last 1e{k} points.

## Technical Requirements

- **Data Handling:** Implement an efficient data structure for real-time data insertion and retrieval of specified requests.
  - We are looking for a single-node, in-memory (no persistent storage) implementation, assuming the server has enough RAM (but not infinite).
  - **Limits:** There will be no more than 10 unique symbols.


- **Concurrency & Performance:** The solution must efficiently handle a high volume of concurrent data entries and statistical requests.
  - 💡 No two concurrent add or/and get requests will occur simultaneously within a given symbol.
  - The time complexity for calculating stats should be better than O(n). O(n) complexity is insufficient for this task.
  - It is ok to use code generation tools like Copilot or ChatGPT, etc.

## Technical Implementation

### Data Structure
https://cp-algorithms.com/data_structures/segment_tree.html
- Uses a segment tree for O(log n) time complexity on range queries (min, max, sum, sum of squares) 
- Supports efficient calculation of min, max, sum, and variance
- Lazy rebuilding strategy for optimal performance
- In-memory storage with no persistence
- Limited to 10 unique symbols

### Performance Characteristics
- O(log n) time complexity for statistical calculations
- Concurrent request handling for different symbols
- Optimized for high-frequency trading scenarios

## Running the Application


2. Build the image:
```bash
docker build -t hft-statistics-api .
```

3. Run the container:
```bash
docker run -p 8000:8000 hft-statistics-api
```


- Run tests:
````bash
docker run hft-statistics-api test
````


- Run tests with coverage:
````bash
docker run hft-statistics-api test-cov
````
