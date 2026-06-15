"""验证 main.py 中 backoff_config 的实际行为。"""
import _bootstrap  # noqa: F401
import sys
from aiogram.utils.backoff import Backoff, BackoffConfig


def assert_eq(name, got, want):
    if got != want:
        print(f"FAIL {name}: got {got!r}, want {want!r}")
        sys.exit(1)
    print(f"OK   {name}")


# main.py 里实际使用的 backoff config
config = BackoffConfig(min_delay=0.5, max_delay=3.0, factor=1.3, jitter=0.1)
backoff = Backoff(config=config)

# 失败 8 次，观察 next_delay 序列
# 由于用了 normalvariate(mu, sigma=0.1) 引入抖动，序列值是浮点的，会偏离
# 公式化的 0.5*1.3^k。这里只验证：
#  1) next_delay 单调不下降（在大方向上）
#  2) next_delay 不会超过 max_delay (3.0) 太多
#  3) 至少在某次 backoff 后 delay >= 1.0
#  4) counter 正确递增

delays = []
for _ in range(8):
    d = next(backoff)
    delays.append(round(d, 4))
print(f"Sample sequence: {delays}")

assert_eq("counter-after-8", backoff.counter, 8)

# 主方向上递增（因为 factor=1.3 > 1）
# jitter=0.1 比较小，所以大部分步会递增
overall_trend = delays[-1] > delays[0]
assert overall_trend, f"no overall growth: {delays}"
print("OK   overall-trend-increasing")

# 末值不超过 max_delay (3.0) + 2*sigma (0.2) + 一点 factor buffer
assert delays[-1] <= 3.6, f"max_delay violated: {delays[-1]}"
print("OK   max-delay-respected")

# 至少一次 delay 突破 1.0（连续失败应该越走越长）
assert any(d >= 1.0 for d in delays[1:]), f"never grew past 1.0: {delays}"
print("OK   grew-past-1.0")

# reset 后回到 min_delay
backoff.reset()
d = next(backoff)
assert 0.4 <= d <= 0.7, f"reset didn't restore min: {d}"
print("OK   reset-restores-min")

print("OK   all backoff smoke tests passed")
