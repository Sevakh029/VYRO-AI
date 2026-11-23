from vyro_backend.degradation import (
    save_degradation_sweep,
    sweep_degradation,
)


def test_degradation_sweep_covers_loss_and_latency_values(tmp_path) -> None:
    configs = sweep_degradation(
        loss_values=(0.0, 0.05),
        latency_values_ms=(0, 200),
        jitter_ms=25,
    )

    assert len(configs) == 4
    assert configs[0].loss == 0.0
    assert configs[-1].latency_ms == 200

    output = tmp_path / "degradation.json"
    save_degradation_sweep(output, configs)
    assert output.exists()
