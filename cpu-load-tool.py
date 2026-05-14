import argparse
import sys
import random
import time
import threading
import math
import psutil
import numpy as np
import signal
import re


def parse_args():
    parser = argparse.ArgumentParser(description='CPU usage monitoring and dynamic adjustment', formatter_class=argparse.RawDescriptionHelpFormatter, epilog='''
Examples:
  cpu-load-tool.py --run_mode once --run_arg1 60
  cpu-load-tool.py --min_ratio 0.3 --max_ratio 0.5
  cpu-load-tool.py --numpy_size 2000000
''')
    parser.add_argument('--loop_count', type=int, default=1000, help='Loop count for each thread (default: 1000)')
    parser.add_argument('--sleep_count_ms', type=int, default=100, help='Sleep ms per iteration (default: 100)')
    parser.add_argument('--sleep_end_ms', type=int, default=5000, help='Sleep ms after loop ends (default: 5000)')
    parser.add_argument('--min_ratio', type=float, default=0.2, help='CPU ratio below min_ratio triggers decrease (default: 0.2)')
    parser.add_argument('--max_ratio', type=float, default=0.4, help='CPU ratio above max_ratio triggers increase (default: 0.4)')
    parser.add_argument('--gather_interval_sec', type=int, default=1, help='Monitoring interval in seconds (default: 1)')
    parser.add_argument('--gather_duration_sec', type=int, default=10, help='Cumulative time in seconds (default: 10)')
    parser.add_argument('--run_mode', type=str, default='once', choices=['once', 'daemon'], help='Run mode: once or daemon (default: once)')
    parser.add_argument('--run_arg1', type=int, default=60, help='Run duration in seconds when run_mode=once (default: 60)')
    parser.add_argument('--numpy_size', type=int, default=1000000, help='Initial numpy array size (default: 1000000)')
    parser.add_argument('--thread_pool_ratio', type=float, default=0.6, help='CPU ratio threshold for thread pool adjustment (default: 0.6)')
    parser.add_argument('--thread_pool_ratio_secs', type=int, default=30, help='Duration in seconds for thread pool adjustment (default: 30)')
    parser.add_argument('--hours', type=str, default='', help='Working hours specification. Format: in[x1,y1],ex[x2,y2]... in=include, ex=exclude. Example: in[9,18],ex[12,13]')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return args


def get_cpu_count():
    return psutil.cpu_count()


def log_print(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} {msg}", flush=True)


def parse_hours_spec(hours_str):
    include_intervals = []
    exclude_intervals = []
    
    if not hours_str:
        return include_intervals, exclude_intervals
    
    pattern = r'(in|ex)\[(\d+),(\d+)\]'
    matches = re.findall(pattern, hours_str)
    
    for match in matches:
        typ, x, y = match
        x, y = int(x), int(y)
        if x < 0:
            x = 0
        if y > 23:
            y = 23
        if typ == 'in':
            include_intervals.append((x, y))
        elif typ == 'ex':
            exclude_intervals.append((x, y))
    
    return include_intervals, exclude_intervals


def is_in_working_hours(include_intervals, exclude_intervals):
    current_hour = time.localtime().tm_hour
    
    if not include_intervals:
        if not exclude_intervals:
            return True
        for ex_x, ex_y in exclude_intervals:
            if ex_x <= ex_y:
                if ex_x <= current_hour <= ex_y:
                    return False
            else:
                if current_hour >= ex_x or current_hour <= ex_y:
                    return False
        return True
    
    for x, y in include_intervals:
        if x <= y:
            if x <= current_hour <= y:
                for ex_x, ex_y in exclude_intervals:
                    if ex_x <= ex_y:
                        if ex_x <= current_hour <= ex_y:
                            return False
                    else:
                        if current_hour >= ex_x or current_hour <= ex_y:
                            return False
                return True
        else:
            if current_hour >= x or current_hour <= y:
                for ex_x, ex_y in exclude_intervals:
                    if ex_x <= ex_y:
                        if ex_x <= ex_y:
                            if ex_x <= current_hour <= ex_y:
                                return False
                        else:
                            if current_hour >= ex_x or current_hour <= ex_y:
                                return False
                return True
    
    return False


def calculation_task():
    data = np.random.rand(config.numpy_size)
    result = np.sin(data) + np.cos(data) + np.sqrt(data) + np.log(data + 1)


def sleep_ms(ms):
    if ms <= 0:
        return
    start = time.time()
    remaining_ms = ms
    while config.running and remaining_ms > 0:
        # 使用 shutdown_event.wait 以便能被中断
        wait_time = min(0.1, remaining_ms / 1000.0)
        shutdown_event.wait(wait_time)
        if shutdown_event.is_set():
            break
        elapsed_ms = (time.time() - start) * 1000
        remaining_ms = ms - elapsed_ms


class Config:
    def __init__(self):
        self.loop_count = 1000
        self.sleep_count_ms = 100
        self.sleep_end_ms = 5000
        self.min_ratio = 0.2
        self.max_ratio = 0.4
        self.gather_interval_sec = 1
        self.gather_duration_sec = 10
        self.run_mode = "once"
        self.run_arg1 = 60
        self.numpy_size = 1000000
        self.thread_pool_ratio = 0.8
        self.thread_pool_ratio_secs = 30
        self.hours = ""
        self.include_intervals = []
        self.exclude_intervals = []
        self.running = True
        self.tls_lock = threading.Lock()
        self.thread_pool_lock = threading.Lock()


config = Config()
worker_threads = []
thread_status = []
max_threads = 0
shutdown_event = threading.Event()  # 用于优雅退出的事件


def signal_handler(signum, frame):
    """信号处理函数，用于优雅退出"""
    signal_name = signal.Signals(signum).name if signum in signal.Signals.__members__.values() else f"signal {signum}"
    log_print(f"[{signal_name}] Received, initiating graceful shutdown...")
    shutdown_event.set()
    config.running = False


def worker_thread_func(thread_id, status_idx):
    while config.running:
        # 等待直到线程被激活
        with config.thread_pool_lock:
            while not thread_status[status_idx] and config.running:
                config.thread_pool_lock.release()
                time.sleep(0.05)  # 更频繁地检查，响应更快
                config.thread_pool_lock.acquire()

        if not config.running:
            break

        # 线程被激活后，立即开始执行任务
        iteration_count = 0
        while config.running:
            # 每次迭代前检查是否还应该运行
            with config.thread_pool_lock:
                if not thread_status[status_idx]:
                    break  # 如果线程被禁用，退出循环回到等待状态

            # 执行计算任务
            calculation_task()

            # 检查是否需要sleep
            with config.tls_lock:
                current_tls = config.sleep_count_ms
            sleep_ms(current_tls)

            iteration_count += 1

            # 完成loop_count次后，短暂休息然后继续（不要等5秒那么久）
            if iteration_count >= config.loop_count:
                with config.thread_pool_lock:
                    if thread_status[status_idx]:
                        # 短暂休息后继续，而不是等5秒
                        sleep_ms(min(500, config.sleep_end_ms))
                iteration_count = 0


def start_worker_threads():
    global max_threads, thread_status, worker_threads
    max_threads = get_cpu_count()
    thread_status = [True] * max_threads
    for i in range(max_threads):
        t = threading.Thread(target=worker_thread_func, args=(i, i))
        t.start()
        worker_threads.append(t)


def get_cpu_ratio():
    return psutil.cpu_percent(interval=None) / 100.0


def adjust_tls(avg):
    with config.tls_lock:
        running_count = sum(1 for s in thread_status if s)
        stopped_count = max_threads - running_count
        target_ratio = (config.min_ratio + config.max_ratio) / 2
        ratio_range = config.max_ratio - config.min_ratio

        if avg < config.min_ratio:
            gap_ratio = (config.min_ratio - avg) / ratio_range
            if config.sleep_count_ms > 1:
                # 当差距很大时，使用更激进的调整策略
                if gap_ratio > 0.5:
                    # 大差距：快速降低，每次至少降到1/3或更小
                    if config.sleep_count_ms > 10000:
                        new_tls = max(1, config.sleep_count_ms // 10)
                    elif config.sleep_count_ms > 1000:
                        new_tls = max(1, config.sleep_count_ms // 5)
                    else:
                        step_factor = min(0.9, 0.5 + gap_ratio * 0.5)
                        new_tls = max(1, int(config.sleep_count_ms * (1 - step_factor)))
                else:
                    # 中等差距：正常调整
                    step_factor = 0.3 + gap_ratio * 0.5
                    new_tls = max(1, int(config.sleep_count_ms * (1 - step_factor)))
                log_print(f"[Dynamic] CPU {avg:.4f} < min {config.min_ratio} | sleep_count_ms {config.sleep_count_ms} -> {new_tls}ms (gap:{gap_ratio:.2f}) | threads: {running_count} running, {stopped_count} stopped")
                config.sleep_count_ms = new_tls
            else:
                if gap_ratio > 0.5:
                    scale_factor = 2.0 + gap_ratio * 0.5
                else:
                    scale_factor = 1.3 + gap_ratio * 0.5
                new_size = int(config.numpy_size * scale_factor)
                log_print(f"[Dynamic] CPU {avg:.4f} < min {config.min_ratio} | sleep_count_ms at min(1ms) | numpy_size {config.numpy_size} -> {new_size} (gap:{gap_ratio:.2f}) | threads: {running_count} running, {stopped_count} stopped")
                config.numpy_size = new_size
        elif avg > config.max_ratio:
            gap_ratio = (avg - config.max_ratio) / ratio_range
            if config.numpy_size > 100000:
                step_factor = 0.3 + gap_ratio * 0.4
                new_size = max(100000, int(config.numpy_size * (1 - step_factor)))
                log_print(f"[Dynamic] CPU {avg:.4f} > max {config.max_ratio} | numpy_size {config.numpy_size} -> {new_size} (gap:{gap_ratio:.2f}) | sleep_count_ms: {config.sleep_count_ms}ms | threads: {running_count} running, {stopped_count} stopped")
                config.numpy_size = new_size
            else:
                step_factor = 0.3 + gap_ratio * 0.4
                new_tls = int(config.sleep_count_ms * (1 + step_factor))
                max_tls = 600000
                if new_tls > max_tls:
                    new_tls = max_tls
                    log_print(f"[Dynamic] CPU {avg:.4f} > max {config.max_ratio} | sleep_count_ms {config.sleep_count_ms} -> {new_tls}ms (capped at 10min) | threads: {running_count} running, {stopped_count} stopped")
                else:
                    log_print(f"[Dynamic] CPU {avg:.4f} > max {config.max_ratio} | sleep_count_ms {config.sleep_count_ms} -> {new_tls}ms (gap:{gap_ratio:.2f}) | threads: {running_count} running, {stopped_count} stopped")
                config.sleep_count_ms = new_tls
        else:
            if running_count > 0:
                cpu_deviation = abs(avg - target_ratio) / ratio_range
                if cpu_deviation < 0.15:
                    config.sleep_count_ms = max(1, config.sleep_count_ms - 1)
                    log_print(f"[FineTune] CPU {avg:.4f} near target | sleep_count_ms {config.sleep_count_ms + 1} -> {config.sleep_count_ms}ms | threads: {running_count} running")


def adjust_thread_pool(avg):
    with config.thread_pool_lock:
        running_count = sum(1 for s in thread_status if s)
        stopped_count = max_threads - running_count

        if avg > config.thread_pool_ratio:
            if running_count > 0:
                stop_count = max(1, running_count // 2)
                stopped = 0
                for i in range(len(thread_status)):
                    if thread_status[i]:
                        thread_status[i] = False
                        stopped += 1
                        if stopped >= stop_count:
                            break
                new_running = running_count - stopped
                log_print(f"[ThreadPool] CPU {avg:.4f} > threshold {config.thread_pool_ratio} | stopped {stopped} threads | threads: {new_running} running, {stopped_count + stopped} stopped")
        elif avg < config.thread_pool_ratio:
            if stopped_count > 0:
                start_count = max(1, stopped_count // 2)
                started = 0
                for i in range(len(thread_status)):
                    if not thread_status[i]:
                        thread_status[i] = True
                        started += 1
                        if started >= start_count:
                            break
                new_running = running_count + started
                log_print(f"[ThreadPool] CPU {avg:.4f} < threshold {config.thread_pool_ratio} | started {started} threads | threads: {new_running} running, {stopped_count - started} stopped")


def monitor_loop(duration_sec, gather_duration_sec, gather_interval_sec, min_ratio, max_ratio):
    cpu_samples = []
    start_time = time.time()
    start_time_first = time.time()
    thread_pool_timer_start = None
    last_thread_pool_action = None
    sample_count = 0
    is_initial_phase = True  # 标记是否为初始调整阶段
    last_hours_state = None  # 记录上一次小时段状态

    while config.running:
        elapsed = time.time() - start_time
        total_elapsed = time.time() - start_time_first

        if total_elapsed >= duration_sec:
            break

        if config.hours:
            current_hours_state = is_in_working_hours(config.include_intervals, config.exclude_intervals)
            if current_hours_state != last_hours_state:
                last_hours_state = current_hours_state
                if current_hours_state:
                    log_print(f"[Hours] Entering working hours, resuming all threads")
                    with config.thread_pool_lock:
                        for i in range(len(thread_status)):
                            thread_status[i] = True
                else:
                    log_print(f"[Hours] Exiting working hours, stopping all threads")
                    with config.thread_pool_lock:
                        for i in range(len(thread_status)):
                            thread_status[i] = False

        if elapsed >= gather_duration_sec:
            if cpu_samples:
                avg = sum(cpu_samples) / len(cpu_samples)
                log_print(f"[Monitor] Avg CPU: {avg:.4f} | Samples: {len(cpu_samples)} | Target: [{min_ratio:.2f}, {max_ratio:.2f}]")
                
                if config.hours and not is_in_working_hours(config.include_intervals, config.exclude_intervals):
                    log_print(f"[Monitor] Outside working hours, skipping dynamic adjustment and thread pool adjustment")
                    thread_pool_timer_start = None
                    last_thread_pool_action = None
                else:
                    adjust_tls(avg)

                    running_count = sum(1 for s in thread_status if s)
                    stopped_count = max_threads - running_count

                    current_state = 'high' if avg > config.thread_pool_ratio else ('low' if avg < config.thread_pool_ratio else 'normal')
                    
                    fast_adjust = is_initial_phase and current_state == 'low' and stopped_count > 0
                    
                    if current_state != 'normal':
                        if last_thread_pool_action != current_state or fast_adjust:
                            adjust_thread_pool(avg)
                            last_thread_pool_action = current_state
                            thread_pool_timer_start = time.time()
                        elif thread_pool_timer_start is not None and time.time() - thread_pool_timer_start >= config.thread_pool_ratio_secs:
                            if current_state == 'high' and running_count > 0:
                                adjust_thread_pool(avg)
                            elif current_state == 'low' and stopped_count > 0:
                                adjust_thread_pool(avg)
                            thread_pool_timer_start = time.time()
                        elif thread_pool_timer_start is None:
                            thread_pool_timer_start = time.time()
                    else:
                        thread_pool_timer_start = None
                        last_thread_pool_action = None
                        if is_initial_phase and min_ratio <= avg <= max_ratio:
                            is_initial_phase = False
                            log_print("[Monitor] CPU reached target range, exiting initial fast adjustment phase")

            cpu_samples = []
            start_time = time.time()
            sample_count = 0
        else:
            cpu_ratio = get_cpu_ratio()
            cpu_samples.append(cpu_ratio)
            sample_count += 1
            time.sleep(gather_interval_sec)


def main():
    args = parse_args()
    config.loop_count = args.loop_count
    config.sleep_count_ms = args.sleep_count_ms
    config.sleep_end_ms = args.sleep_end_ms
    config.min_ratio = args.min_ratio
    config.max_ratio = args.max_ratio
    config.gather_interval_sec = args.gather_interval_sec
    config.gather_duration_sec = args.gather_duration_sec
    config.run_mode = args.run_mode
    config.run_arg1 = args.run_arg1
    config.numpy_size = args.numpy_size
    config.thread_pool_ratio = args.thread_pool_ratio
    config.thread_pool_ratio_secs = args.thread_pool_ratio_secs
    config.hours = args.hours
    if config.hours:
        config.include_intervals, config.exclude_intervals = parse_hours_spec(config.hours)
    else:
        config.include_intervals = [0,23] #默认 0-23 小时
        config.exclude_intervals = []
    print(f"Configuration:", flush=True)
    print(f"  loop_count: {config.loop_count}", flush=True)
    print(f"  sleep_count_ms: {config.sleep_count_ms}", flush=True)
    print(f"  sleep_end_ms: {config.sleep_end_ms}", flush=True)
    print(f"  min_ratio: {config.min_ratio}", flush=True)
    print(f"  max_ratio: {config.max_ratio}", flush=True)
    print(f"  gather_interval_sec: {config.gather_interval_sec}", flush=True)
    print(f"  gather_duration_sec: {config.gather_duration_sec}", flush=True)
    print(f"  run_mode: {config.run_mode}", flush=True)
    if config.run_mode == 'once':
        print(f"  run_arg1 (duration): {config.run_arg1}", flush=True)
    print(f"  numpy_size: {config.numpy_size}", flush=True)
    print(f"  thread_pool_ratio: {config.thread_pool_ratio}", flush=True)
    print(f"  thread_pool_ratio_secs: {config.thread_pool_ratio_secs}", flush=True)
    if config.hours:
        print(f"  hours: {config.hours}", flush=True)
        print(f"    include intervals: {config.include_intervals}", flush=True)
        print(f"    exclude intervals: {config.exclude_intervals}", flush=True)
    print(f"  CPU count: {get_cpu_count()}", flush=True)
    print("Starting worker threads and monitoring...", flush=True)

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print("Registered signal handlers for SIGINT (Ctrl+C) and SIGTERM", flush=True)

    start_worker_threads()

    # 根据小时段配置决定初始线程状态
    cpu_count = get_cpu_count()
    if config.hours:
        if is_in_working_hours(config.include_intervals, config.exclude_intervals):
            initial_active = max(1, cpu_count // 3)
            log_print(f"[Hours] Currently in working hours, starting with {initial_active}/{cpu_count} threads")
        else:
            initial_active = 0
            log_print(f"[Hours] Currently outside working hours, starting with {initial_active}/{cpu_count} threads")
    else:
        initial_active = max(1, cpu_count // 3)
        log_print(f"Starting with {initial_active}/{cpu_count} threads active to avoid high initial CPU load")
    
    with config.thread_pool_lock:
        for i in range(cpu_count):
            thread_status[i] = (i < initial_active)

    try:
        if config.run_mode == 'once':
            monitor_loop(config.run_arg1, config.gather_duration_sec, config.gather_interval_sec, config.min_ratio, config.max_ratio)
            log_print("Run mode 'once' completed.")
        else:
            log_print("Running in daemon mode. Press Ctrl+C to stop.")
            monitor_loop(float('inf'), config.gather_duration_sec, config.gather_interval_sec, config.min_ratio, config.max_ratio)
    except KeyboardInterrupt:
        log_print("[Ctrl+C] Initiating graceful shutdown...")
    finally:
        log_print("[Shutdown] Setting running flag to False...")
        config.running = False
        
        log_print("[Shutdown] Activating all threads to allow them to exit...")
        with config.thread_pool_lock:
            for i in range(len(thread_status)):
                thread_status[i] = True
        
        log_print(f"[Shutdown] Waiting for {len(worker_threads)} worker threads to exit...")
        for i, t in enumerate(worker_threads):
            try:
                t.join(timeout=3)
                if t.is_alive():
                    log_print(f"[Shutdown] Thread {i} did not exit in time")
                else:
                    log_print(f"[Shutdown] Thread {i} exited successfully")
            except Exception as e:
                log_print(f"[Shutdown] Error joining thread {i}: {e}")
        
        log_print("[Shutdown] All threads exited. Goodbye!")


if __name__ == '__main__':
    main()
