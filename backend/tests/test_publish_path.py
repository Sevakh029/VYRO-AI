from vyro_backend.publish_path import PublishPath


def test_publish_path_drops_messages_when_configured() -> None:
    def publisher() -> None:
        raise AssertionError("should not publish")

    path = PublishPath(drop_probability=1.0, seed=100)

    assert path.publish(publisher) is False


def test_publish_path_calls_publisher_when_no_degradation() -> None:
    calls: list[str] = []
    path = PublishPath()

    assert path.publish(lambda: calls.append("published")) is None
    assert calls == ["published"]
