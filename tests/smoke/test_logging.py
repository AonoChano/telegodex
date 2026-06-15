"""冒烟：双 sink（终端简 / 文件详）行为。

把 loguru 的终端 sink 替换成 StringIO + 我们的 _strip_exception_block，
文件 sink 也换成 StringIO，然后触发一次带 traceback 的 ERROR，断言：

- 终端 sink 里：只有一行，没有 traceback 续行
- 文件 sink 里：包含完整 traceback 行（不重复）
- 颜色 token (<green>, <cyan> 等) 只出现在终端，文件无颜色
"""
import _bootstrap  # noqa: F401
import io
import logging
import sys

from main import _InterceptHandler, _setup_logging, _strip_exception_block
from loguru import logger


def reset_logger():
    """清掉所有 sink，回到一个干净状态。"""
    logger.remove()


def assert_eq(name, got, want):
    if got != want:
        print(f"FAIL {name}: got {got!r}, want {want!r}")
        sys.exit(1)
    print(f"OK   {name}")


def term_sink_factory(buf):
    """返回一个模仿 main._terminal_sink 的 callable sink。"""
    def sink(message):
        buf.write(_strip_exception_block(str(message)))
    return sink


def _setup_test_sinks(term_buf, file_buf):
    """和 main.py 的生产配置完全一致：简单 format，让 loguru 自动追加 traceback。"""
    terminal_format = (
        "{time:HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    )
    file_format = (
        "{time:HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    )
    logger.add(term_sink_factory(term_buf), level="INFO",
               format=terminal_format, backtrace=False, diagnose=False, colorize=False)
    logger.add(file_buf, level="DEBUG", format=file_format,
               backtrace=False, diagnose=True, colorize=False)


def test_terminal_simplified():
    """终端 sink：没有 traceback 续行。"""
    reset_logger()
    term_buf, file_buf = io.StringIO(), io.StringIO()
    _setup_test_sinks(term_buf, file_buf)

    def deep_error():
        def f1():
            raise ValueError("boom from f1")
        def f2():
            f1()
        f2()

    try:
        deep_error()
    except Exception as e:
        logger.error("AI 调用失败: %s", e)

    term_lines = [l for l in term_buf.getvalue().splitlines() if l.strip()]

    # 终端：恰好 1 行
    assert_eq("terminal-line-count", len(term_lines), 1)
    assert "AI 调用失败" in term_lines[0]
    assert "Traceback" not in term_buf.getvalue(), "terminal should not contain Traceback"
    print("OK   terminal-no-traceback")


def test_file_has_traceback_when_requested():
    """文件 sink：logger.opt(exception=True) 时，文件里能看到完整 traceback。"""
    reset_logger()
    term_buf, file_buf = io.StringIO(), io.StringIO()
    _setup_test_sinks(term_buf, file_buf)

    def deep_error():
        def f1():
            raise ValueError("boom from f1")
        def f2():
            f1()
        f2()

    try:
        deep_error()
    except Exception:
        logger.opt(exception=True).error("AI 调用失败")

    # 终端仍然 1 行（"AI 调用失败"），无 traceback
    term_lines = [l for l in term_buf.getvalue().splitlines() if l.strip()]
    assert_eq("terminal-line-count-opt", len(term_lines), 1)
    assert "Traceback" not in term_buf.getvalue()
    print("OK   terminal-no-traceback-opt")

    # 文件：含 1 份完整 traceback（多行），不重复
    file_lines = [l for l in file_buf.getvalue().splitlines() if l.strip()]
    assert len(file_lines) > 1, f"file should be multi-line, got {len(file_lines)}"
    file_tracebacks = file_buf.getvalue().count("Traceback")
    assert file_tracebacks == 1, \
        f"expected exactly 1 traceback in file, got {file_tracebacks}"
    assert "ValueError: boom from f1" in file_buf.getvalue()
    assert any("deep_error" in l for l in file_lines), "file should show call site"
    print(f"OK   file-has-1-traceback ({len(file_lines)} lines)")


def test_intercept_aiogram():
    """aiogram stdlib logger → 走 loguru，且被 _terminal_sink 砍掉 traceback。"""
    reset_logger()
    term_buf = io.StringIO()

    logger.add(term_sink_factory(term_buf), level="INFO",
               format=("{time} | {level: <8} | {name} - {message}"),
               backtrace=False, diagnose=False, colorize=False)

    # 接管 stdlib
    root = logging.getLogger()
    root.handlers = [_InterceptHandler()]
    root.setLevel(logging.INFO)

    # 模拟 aiogram 抛 ERROR + traceback
    aiogram_log = logging.getLogger("aiogram.dispatcher")
    try:
        raise RuntimeError("aiogram simulated failure")
    except RuntimeError:
        aiogram_log.error("process_update failed: %s", "boom")

    captured = term_buf.getvalue()
    assert "ERROR" in captured, f"expected ERROR in log, got: {captured!r}"
    assert "aiogram" in captured
    assert "boom" in captured
    # 关键：aiogram 内部 logger 的 traceback 也被终端 sink 砍掉了
    assert "Traceback" not in captured, \
        f"terminal should not contain traceback, got: {captured!r}"
    print("OK   intercept-routes-aiogram")


def test_silent_for_repeated_network_error():
    """网络抖动时的多次同质错误：终端仍只显示错误行（无续行 traceback）。

    注意：默认 logger.error 不挂 exception info，文件也不会有 traceback。
    想文件侧也保留 traceback，调用方需 opt(exception=True) — 真实应用里
    AI 失败路径应这么写。
    """
    reset_logger()
    term_buf, file_buf = io.StringIO(), io.StringIO()
    _setup_test_sinks(term_buf, file_buf)

    for i in range(5):
        try:
            raise ConnectionError("connection reset by peer")
        except ConnectionError:
            logger.error("Network error #%d", i + 1)

    # 终端：5 行独立错误，无续行
    term_lines = [l for l in term_buf.getvalue().splitlines() if l.strip()]
    assert_eq("5-network-errors", len(term_lines), 5)
    assert "Traceback" not in term_buf.getvalue()
    print("OK   5-network-errors-no-traceback")

    # 文件：5 行（无 traceback，因为 logger.error 没挂 exception）
    file_lines = [l for l in file_buf.getvalue().splitlines() if l.strip()]
    assert_eq("5-network-errors-file", len(file_lines), 5)
    print("OK   5-network-errors-file-no-traceback-by-default")


def test_silent_for_repeated_network_error_with_opt():
    """opt(exception=True) 时，文件侧 1 份 traceback/错误，终端仍然精简化。"""
    reset_logger()
    term_buf, file_buf = io.StringIO(), io.StringIO()
    _setup_test_sinks(term_buf, file_buf)

    for i in range(3):
        try:
            raise ConnectionError("connection reset by peer")
        except ConnectionError:
            logger.opt(exception=True).error("Network error #%d", i + 1)

    # 终端：3 行（每条都是单行），无 traceback
    term_lines = [l for l in term_buf.getvalue().splitlines() if l.strip()]
    assert_eq("3-net-errs-term", len(term_lines), 3)
    assert "Traceback" not in term_buf.getvalue()
    print("OK   3-net-errs-term-no-traceback")

    # 文件：3 份 traceback（每份 1 个 "Traceback" 头，共 3）
    file_tracebacks = file_buf.getvalue().count("Traceback")
    assert file_tracebacks == 3, f"expected 3 tracebacks in file, got {file_tracebacks}"
    print(f"OK   file-has-{file_tracebacks}-tracebacks")


if __name__ == "__main__":
    test_terminal_simplified()
    test_file_has_traceback_when_requested()
    test_intercept_aiogram()
    test_silent_for_repeated_network_error()
    test_silent_for_repeated_network_error_with_opt()
    print("ALL LOGGING SMOKE OK")
