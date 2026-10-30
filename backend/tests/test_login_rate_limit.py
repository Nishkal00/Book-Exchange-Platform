from app.login_rate_limit import LoginRateLimiter


def test_blocks_after_five_failures():
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)

    for timestamp in range(100, 105):
        limiter.record_failure("Student@Example.edu", "127.0.0.1", now=timestamp)

    assert limiter.retry_after("student@example.edu", "127.0.0.1", now=105) == 895


def test_email_and_ip_are_isolated():
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)

    for timestamp in range(100, 105):
        limiter.record_failure("student@example.edu", "127.0.0.1", now=timestamp)

    assert limiter.retry_after("student@example.edu", "127.0.0.2", now=105) is None
    assert limiter.retry_after("other@example.edu", "127.0.0.1", now=105) is None


def test_success_clears_failures():
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)

    for timestamp in range(100, 104):
        limiter.record_failure("student@example.edu", "127.0.0.1", now=timestamp)

    limiter.record_success("student@example.edu", "127.0.0.1")

    assert limiter.retry_after("student@example.edu", "127.0.0.1", now=105) is None


def test_expired_failures_are_removed():
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)

    for timestamp in range(100, 105):
        limiter.record_failure("student@example.edu", "127.0.0.1", now=timestamp)

    limiter.cleanup(now=1005)

    assert limiter.retry_after("student@example.edu", "127.0.0.1", now=1005) is None
    assert ("student@example.edu", "127.0.0.1") not in limiter._failures


def test_old_failures_stop_counting_in_rolling_window():
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)

    for timestamp in (100, 101, 102, 103, 104):
        limiter.record_failure("student@example.edu", "127.0.0.1", now=timestamp)

    # At 1005, all five failures have expired.
    assert limiter.retry_after("student@example.edu", "127.0.0.1", now=1005) is None
