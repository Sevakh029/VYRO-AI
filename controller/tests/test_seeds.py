from vyro_controller import TEST_SEEDS, TUNING_SEEDS


def test_tuning_seeds_are_explicit() -> None:
    assert TUNING_SEEDS == (1, 2, 3, 4, 5)


def test_test_seeds_are_never_mixed_with_tuning() -> None:
    assert TEST_SEEDS == tuple(range(100, 110))
    assert set(TEST_SEEDS).isdisjoint(TUNING_SEEDS)

