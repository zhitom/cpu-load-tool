# cpu-load-tool

## Project Description

Monitors total CPU usage and dynamically adjusts CPU load when it falls below or exceeds specified thresholds.

## Workflow

### Configuration Options

- Thread Configuration:
  - loop_count: Number of iterations per thread, default 1000
  - sleep_count_ms: Sleep duration per iteration in milliseconds, default 100ms
  - sleep_end_ms: Sleep duration after loop completes in milliseconds, default 5000ms
  
- Thread Pool Configuration:
  - thread_pool_ratio: When CPU usage exceeds this value for longer than thread_pool_ratio_secs, stop half of the threads. If CPU remains high, continue stopping half of remaining threads until all are stopped. Default: 0.6. If CPU drops below this value, thread stopping stops. If CPU stays below this value for thread_pool_ratio_secs, start half of stopped threads. Continue until all threads are running [total threads does not exceed initial count].
  - thread_pool_ratio_secs: Duration threshold for CPU to remain above or below thread_pool_ratio, default 30 seconds
  
- Dynamic Adjustment Configuration:
  - min_ratio: CPU ratio below which triggers decrease rules, default 0.2 (1.0 = full CPU)
  - max_ratio: CPU ratio above which triggers increase rules, default 0.4 (1.0 = full CPU)
  
- Monitoring Configuration:
  - gather_interval_sec: Monitoring interval in seconds, default 1 second
  - gather_duration_sec: Cumulative monitoring duration, default 10 seconds
  
- Run Mode Configuration:
  - run_mode: Run mode, default 'once' or 'daemon'
  - run_arg1: Run argument 1, when run_mode=once, default 60 seconds; not needed for daemon mode

### Initialization

- Start CPU monitoring thread
- Start threads equal to CPU core count
- Command line parameters specify loop_count (e.g., 1000), sleep_count_ms, and sleep_end_ms
  - Each thread performs random calculations loop_count times, sleeping sleep_count_ms each iteration
    - Calculation rules:
      - Random number generation
      - Current time retrieval
      - Float calculation (random number 0-10000 divided by 0.19, floor)
      - Randomly select one of the above three methods based on cumulative count
  - After loop_count iterations, sleep for sleep_end_ms
  - If sleep_end_ms exceeds 3s, split into multiple 3s sleeps

### Dynamic Rules

- CPU Monitoring Thread:
  - Monitor total CPU usage every gather_interval_sec seconds, accumulate t samples over gather_duration_sec, calculate average: avg = (c1 + c2 + ... + ct) / t
  - If avg < min_ratio: trigger dynamic adjustment to decrease sleep time
  - If avg > max_ratio: trigger dynamic adjustment to increase sleep time
  - Reset collected data and begin next monitoring cycle
  - Dynamic Adjustment Rules:
    - Decrease Rule:
      - Reduce sleep_count_ms by half for each thread, minimum 1ms
    - Increase Rule:
      - Increase sleep_count_ms by half for each thread, maximum 10 minutes

## Implementation

- Implemented in Python, packaged as Linux executable
- Supports both Windows and Linux
- Uses venv for Python environment management
- Generates requirements.txt for dependencies

## Execution Commands

### Packaged Executable

```bash
# Windows
dist\cpu-load-tool.exe --run_mode once --run_arg1 60

# Linux
./dist/cpu-load-tool --run_mode once --run_arg1 60
```

### Direct Python Execution

```bash
# Install dependencies
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Run
python cpu-load-tool.py --run_mode once --run_arg1 60
```

### Parameter Description

| Parameter               | Description                                      | Default |
| ------------------------| -------------------------------------------------| --------|
| --loop_count            | Number of iterations per thread                  | 1000    |
| --sleep_count_ms        | Sleep ms per iteration                           | 100     |
| --sleep_end_ms          | Sleep ms after loop completes                    | 5000    |
| --min_ratio             | CPU ratio below which reduces sleep (min 1ms)    | 0.2     |
| --max_ratio             | CPU ratio above which increases sleep            | 0.4     |
| --gather_interval_sec   | Monitoring interval in seconds                   | 1       |
| --gather_duration_sec   | Cumulative monitoring duration in seconds        | 10      |
| --run_mode              | Run mode: once/daemon                            | once    |
| --run_arg1              | Duration in seconds (when run_mode=once)         | 60      |
| --numpy_size            | Initial numpy array size (for CPU load adjustment)| 1000000 |
| --thread_pool_ratio     | CPU threshold for thread pool adjustment         | 0.6     |
| --thread_pool_ratio_secs| Duration threshold for CPU anomaly               | 30      |

### Run Modes

```bash
# once mode: Run for specified duration then exit
dist\cpu-load-tool.exe --run_mode once --run_arg1 60

# daemon mode: Run continuously until Ctrl+C
dist\cpu-load-tool.exe --run_mode daemon
```

### Examples

```bash
# Basic usage (run for 60 seconds then exit)
dist\cpu-load-tool.exe

# Custom duration and monitoring parameters
dist\cpu-load-tool.exe --run_mode once --run_arg1 30 --gather_duration_sec 5

# Adjust CPU target range (0.3-0.5)
dist\cpu-load-tool.exe --min_ratio 0.3 --max_ratio 0.5

# Adjust numpy array size (affects CPU load)
dist\cpu-load-tool.exe --numpy_size 2000000
```