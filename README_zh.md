# cpu-load-tool

## 项目介绍

监测cpu总占比，如果小于指定值或高于指定值时对cpu进行动态调整

## 流程

### 配置项

- 线程配置项
  - loop_count：循环次数，默认循环1000次
  - sleep_count_ms：每次的睡眠ms数，默认100ms
  - sleep_end_ms：循环结束后的睡眠ms数，默认5000ms
- 线程池配置项
  - thread_pool_ratio: cpu占比高于此数值并且持续时间超过thread_pool_ratio_secs秒时停止一半的线程，如果后续cpu占比一直持续高于此数值，再停止剩余线程数的一半，直到线程数全部停止，默认thread_pool_ratio=0.6；如果中间cpu占比出现低于此数值就不再停止线程；如果最后cpu占比持续低于此数值并且持续时间超过thread_pool_ratio_secs秒，将启动剩余未启动线程数一半的线程，如果后续cpu占比一直持续低于此数值，再启动剩余未启动线程数一半的线程，直到全部线程数都启动【总线程数不超过初始线程数】
  - thread_pool_ratio_secs：cpu占比持续高于或持续低于thread_pool_ratio值的持续时间，默认thread_pool_ratio_secs=30秒
- 动态调整配置项
  - min_ratio：cpu占比占比低于min_ratio值时触发变小规则，默认min_ratio=0.2；cpu满跑为1.0
  - max_ratio：cpu占比占比高于max_ratio值时触发变大规则，默认max_ratio=0.4；cpu满跑为1.0
- 监测采集配置项
  - gather_interval_sec：监测间隔，比如每n秒监测一次，默认gather_interval_sec=1秒
  - gather_duration_sec：累计时间，默认gather_duration_sec=10秒
- 运行模式配置项
  - run_mode：运行模式，默认run_mode=once|daemon
  - run_arg1: 运行参数1，当run_mode=once时，默认run_arg1=60秒，当run_mode=daemon时，不需要此参数

### 初始化

- 启动cpu监测线程
- 启动和cpu个数相同的线程数
- 由命令行参数指定循环次数loop_count【比如循环1000次】、每次的睡眠ms数sleep_count_ms、循环结束后的睡眠ms数sleep_end_ms
  - 每个线程随机进行计算loop_count次，每次睡眠指定的ms数sleep_count_ms
    - 计算规则：
      - 随机数计算
      - 获取当前时间
      - 浮点数计算（0-10000随机数除以0.19向下规整）
      - 按累计次数随机选择上面3种方式之一进行计算
  - loop_count次计算结束后，再次睡眠指定的ms数sleep_end_ms
  - 如果sleep_end_ms超过3s，将其拆分多次睡眠，每次睡眠3s，总睡眠时间不超过sleep_end_ms

### 动态规则

- cpu监测线程：
  - 每gather_interval_sec秒监测cpu总占比c，在gather_duration_sec秒内累计t次监测，计算cpu平均值avg=(c1+c2+...+ct)/t
  - 如果avg低于min_ratio，触发动态调整，将睡眠时间变小
  - 如果avg高于max_ratio，触发动态调整，将睡眠时间变大
  - 然后将采集数据清零再重新采集cpu占比，进入下一次循环
  - 动态调整规则：
    - 变小规则：
      - 将每个线程的sleep_count_ms睡眠ms数减少sleep_count_ms/2，最小值为1ms
    - 变大规则：
      - 将每个线程的sleep_count_ms睡眠ms数增加sleep_count_ms/2，最大值限制为10分钟

## 实现

- 使用python实现，并打包成linux可执行文件，支持windows和linux系统
- 使用venv管理python环境
- 生成python的依赖文件requirements.txt

## 执行命令

### 打包后的可执行文件

```bash
# Windows
dist\cpu-load-tool.exe --run_mode once --run_arg1 60

# Linux
./dist/cpu-load-tool --run_mode once --run_arg1 60
```

### Python直接运行

```bash
# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 运行
python cpu-load-tool.py --run_mode once --run_arg1 60
```

### 参数说明

| 参数                     | 说明                                      | 默认值  |
| ------------------------ | ----------------------------------------- | ------- |
| --loop_count             | 每个线程的循环次数                        | 1000    |
| --sleep_count_ms         | 每次循环的睡眠毫秒数                      | 100     |
| --sleep_end_ms           | 循环结束后的睡眠毫秒数                    | 5000    |
| --min_ratio              | CPU占比低于此值时减小sleep（最小1ms）     | 0.2     |
| --max_ratio              | CPU占比高于此值时增大sleep                | 0.4     |
| --gather_interval_sec    | 监测间隔（秒）                            | 1       |
| --gather_duration_sec    | 累计监测时间（秒）                        | 10      |
| --run_mode               | 运行模式：once/daemon                     | once    |
| --run_arg1               | 运行持续时间（run_mode=once时，单位：秒） | 60      |
| --numpy_size             | 初始numpy数组大小（用于CPU负载调整）      | 1000000 |
| --thread_pool_ratio      | CPU占比阈值，高于或低于此值时调整线程池   | 0.6     |
| --thread_pool_ratio_secs | CPU占比持续异常的时间阈值（秒）           | 30      |

### 运行模式

```bash
# once模式：运行指定时间后自动退出
dist\cpu-load-tool.exe --run_mode once --run_arg1 60

# daemon模式：持续运行，直到Ctrl+C中断
dist\cpu-load-tool.exe --run_mode daemon
```

### 示例

```bash
# 基础用法（运行60秒后退出）
dist\cpu-load-tool.exe

# 自定义运行时间和监测参数
dist\cpu-load-tool.exe --run_mode once --run_arg1 30 --gather_duration_sec 5

# 调整CPU目标区间（0.3-0.5）
dist\cpu-load-tool.exe --min_ratio 0.3 --max_ratio 0.5

# 调整numpy数组大小（影响CPU负载）
dist\cpu-load-tool.exe --numpy_size 2000000
```
