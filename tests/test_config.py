from pathlib import Path

from l10_hand_control.config import HandConfig, load_config


def test_default_config_targets_l10_left_on_pcan():
    config = HandConfig()

    assert config.hand_type == "left"
    assert config.hand_joint == "L10"
    assert config.can == "PCAN_USBBUS1"
    assert config.dashboard_url == "http://127.0.0.1:7080"


def test_load_config_overrides_yaml_values(tmp_path: Path):
    config_file = tmp_path / "hand.yaml"
    config_file.write_text(
        "\n".join(
            [
                "hand_type: right",
                "hand_joint: L10",
                "can: PCAN_USBBUS2",
                "dashboard_url: http://127.0.0.1:9999",
                "sdk_path: C:/sdk/linkerhand-python-sdk",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.hand_type == "right"
    assert config.can == "PCAN_USBBUS2"
    assert config.dashboard_url == "http://127.0.0.1:9999"
    assert config.sdk_path == Path("C:/sdk/linkerhand-python-sdk")
