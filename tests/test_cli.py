import csv
import glob
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from bqat.app import benchmark, filter, preprocess, report, run


@pytest.fixture(scope="session")
def extracted_samples(tmp_path_factory):
    base_tmp = tmp_path_factory.mktemp("samples")
    sample_modes = ["face", "iris", "finger", "speech"]  # add others if needed

    for mode in sample_modes:
        zip_path = Path("tests/samples") / f"{mode}.zip"
        dest = base_tmp / mode
        dest.mkdir(parents=True, exist_ok=True)
        with ZipFile(zip_path, "r") as z:
            z.extractall(dest)

    return base_tmp  # contains subfolders: base_tmp/face, base_tmp/speech


@pytest.mark.parametrize(
    "mode,single,reporting,engine",
    [
        ("face", False, True, ""),  # was test_face_normal_default
        ("face", False, False, ""),  # was test_face_normal_single
        ("face", False, False, "biqt"),  # was test_face_normal_biqt,
        ("face", False, False, "ofiq"),  # was test_face_normal_ofiq
        ("finger", False, False, ""),
        ("iris", False, False, ""),
        ("speech", False, False, ""),
        ("speech", True, False, ""),
    ],
)
def test_all_engines(extracted_samples, tmp_path, mode, single, reporting, engine):
    """
    GIVEN a set of mock face images
    WHEN processed by the default engine with different 'single' settings
    THEN output files should be valid
    """
    input_dir = extracted_samples / mode
    output_dir = tmp_path / "output"

    if engine == "ofiq":
        input_dir = extracted_samples / mode / "face"

    run(
        mode=mode,
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=0,
        pattern="*",
        single=single,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
        reporting=reporting,
        engine=engine,
        debugging=False,
    )

    outputs = glob.glob(str(output_dir) + "/*")

    if reporting is True:
        assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().startswith("<!doctype html>")
        elif path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.readline()) is True
            if reporting is False:
                assert len(outputs) == 2
        elif path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_filter_combine(extracted_samples, tmp_path):
    mode = "finger"
    input_dir = extracted_samples / mode
    output_dir = tmp_path / "output"

    run(
        mode=mode,
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=8,
        pattern="*",
        single=False,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="bmp",
        attributes="NFIQ2",
        query="NFIQ2>0",
        sort="NFIQ2",
        cwd="",
        reporting=False,
        engine="",
        debugging=False,
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 2
    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.read()) == True
            # assert len(outputs) == 5
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_filter_standalone(extracted_samples, tmp_path):
    mode = "finger"
    input_dir = extracted_samples / mode
    output_dir = tmp_path / "output"

    run(
        mode=mode,
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=10,
        pattern="*",
        single=False,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
        reporting=False,
        engine="",
        debugging=False,
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 2

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0

        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]

        if path.endswith(".csv"):
            dir = filter(path, attributes="NFIQ2", query="NFIQ2>10", sort="", cwd="")
            assert dir.get("output").endswith(".csv") == True
            with open(dir.get("output")) as f:
                assert csv.Sniffer().has_header(f.read()) == True
            assert dir.get("report").endswith(".html") == True
            with open(dir.get("report")) as f:
                assert f.readline().find("<!doctype html>") == 0
            outputs = glob.glob(str(output_dir) + "/*")
            assert len(outputs) == 5
            if path.endswith(".csv"):
                with open(path) as f:
                    assert csv.Sniffer().has_header(f.read()) == True


def test_preprocess_standalone(extracted_samples, tmp_path, capsys):
    mode = "finger"
    input_dir = extracted_samples / mode
    output_dir = tmp_path / "output"

    config = {
        "target": "png",
        "grayscale": "true",
        "rgb": "true",
        "width": "100",
        "frac": 0.5,
    }
    preprocess(str(input_dir), str(output_dir), True, config)
    captured = capsys.readouterr()
    assert "Preprocessing Task Finished" in captured.out
    # outputs = glob.glob(f"{output_dir}/**/*", recursive=True)
    # assert len(outputs) == 5

def test_report_standalone(capsys):
    input_dir = Path("tests/samples/data.csv")

    report(str(input_dir), cwd="")
    captured = capsys.readouterr()
    assert "EDA Report" in captured.out


@pytest.mark.parametrize(
    "mode,limit,single,engine",
    [
        ("face", None, False, ""),
        ("face", None, False, "ofiq"),
        ("face", 5, True, ""),
        ("speech", None, False, ""),
        ("finger", None, False, ""),
        ("iris", None, False, ""),
    ],
)
def test_benchmark(capsys, mode: str, limit: int, single: bool, engine: str):
    """
    GIVEN a set of mock face images
    WHEN processed by the default engine with different 'single' settings
    THEN output files should be valid
    """
    benchmark(mode=mode, limit=limit, single=single, engine=engine)
    captured = capsys.readouterr()
    assert "Benchmarking Finished" in captured.out
