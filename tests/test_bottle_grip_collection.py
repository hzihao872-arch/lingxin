from examples.bottle_grip_collection import (
    BOTTLE_GRIP_TRIALS,
    L10_JOINTS,
    append_result,
    trial_pose,
)


def test_bottle_trials_build_valid_l10_poses():
    assert len(BOTTLE_GRIP_TRIALS) >= 20

    for trial in BOTTLE_GRIP_TRIALS:
        pose = trial_pose(trial)
        assert len(pose) == 10
        assert all(isinstance(value, int) for value in pose)
        assert all(0 <= value <= 255 for value in pose)


def test_append_result_writes_csv_header_and_trial_row(tmp_path):
    csv_path = tmp_path / "results.csv"
    trial = BOTTLE_GRIP_TRIALS[0]

    append_result(csv_path, trial_number=1, trial=trial, success=1)

    lines = csv_path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    row = lines[1].split(",")

    assert "timestamp" in header
    assert "trial_number" in header
    assert "trial_name" in header
    assert "success" in header
    assert all(joint in header for joint in L10_JOINTS)
    assert row[header.index("trial_number")] == "1"
    assert row[header.index("trial_name")] == trial["name"]
    assert row[header.index("success")] == "1"
