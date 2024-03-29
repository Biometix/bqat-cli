import csv
import glob
import json
import shutil
from zipfile import ZipFile

from bqat.app import filter, run


def test_face_normal_default(tmp_path):
    """
    GIVEN a set of mock face images
    WHEN the images processed by the default engine
    THEN check if the output files are properly generated
    """
    samples = "tests/samples/face.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)

    run(
        mode="face",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=0,
        pattern="*",
        single=False,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.readline()) == True
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_finger_normal_default(tmp_path):
    """
    GIVEN a set of mock fingerprint images
    WHEN the images processed by the default engine
    THEN check if the output files are properly generated
    """
    samples = "tests/samples/finger.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)

    run(
        mode="finger",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=0,
        pattern="*",
        single=False,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.read()) == True
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_iris_normal_default(tmp_path):
    """
    GIVEN a set of mock iris images
    WHEN the images processed by the default engine
    THEN check if the output files are properly generated
    """
    samples = "tests/samples/iris.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)

    run(
        mode="iris",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=0,
        pattern="*",
        single=False,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.read()) == True
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_face_single(tmp_path):
    """
    GIVEN a set of mock face images
    WHEN the images processed by the default engine
    THEN check if the output files are properly generated by single thread processing
    """
    samples = "tests/samples/face.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)

    run(
        mode="face",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=0,
        pattern="*",
        single=True,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                # assert csv.Sniffer().has_header(f.read()) == True
                assert f.readline().count("file") == True
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_face_limit(tmp_path):
    """
    GIVEN a set of mock face images
    WHEN the images processed by the default engine
    THEN check if the output files are properly generated with file number limit
    """
    LIMIT = 5
    samples = "tests/samples/face.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)

    run(
        mode="face",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=LIMIT,
        pattern="*",
        single=False,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                reader = [row for row in csv.DictReader(f)]
                entries = len(reader)
        if path.endswith(".json"):
            with open(path) as f:
                log = json.loads(f.read())
                assert list(log.keys()) == ["metadata", "log"]

    assert entries == LIMIT - len(
        [record for record in log["log"] if "load image" in list(record.keys())]
    )


def test_filter_combine(tmp_path):
    samples = "tests/samples/finger.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)

    run(
        mode="finger",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=10,
        pattern="*",
        single=False,
        type=["wsq", "jpg", "jpeg", "png", "bmp", "jp2"],
        convert="",
        target="",
        attributes="NFIQ2,Width",
        query="NFIQ2 > 0 and Width < 300",
        sort="NFIQ2",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 5

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.read()) == True
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_filter_standalone(tmp_path):
    samples = "tests/samples/finger.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)

    run(
        mode="finger",
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
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.read()) == True
            dir = filter(path, attributes="NFIQ2", query="NFIQ2>10", sort="", cwd="")
            assert dir.get("output").endswith(".html") == True
            with open(dir.get("output")) as f:
                assert f.readline().find("<!doctype html>") == 0
            assert dir.get("report").endswith(".html") == True
            with open(dir.get("report")) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_speech_single(tmp_path):
    """
    GIVEN a set of mock speech samples
    WHEN the samples processed with single run mode
    THEN check if the output files are properly generated
    """
    samples = "tests/samples/speech.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)
    input_file = str(list(input_dir.glob("**/*.wav"))[0])
    for index in range(3):
        shutil.copy(input_file, input_dir / f"input_file_{index}.wav")

    run(
        mode="speech",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=0,
        pattern="*",
        single=True,
        type=["wav"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.readline()) == True
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]


def test_speech_batch(tmp_path):
    """
    GIVEN a set of mock speech samples
    WHEN the samples processed with batch run mode
    THEN check if the output files are properly generated
    """
    samples = "tests/samples/speech.zip"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    with ZipFile(samples, "r") as z:
        z.extractall(input_dir)
    input_file = str(list(input_dir.glob("**/*.wav"))[0])
    for index in range(3):
        shutil.copy(input_file, input_dir / f"input_file_{index}.wav")

    run(
        mode="speech",
        input_folder=str(input_dir),
        output_folder=str(output_dir),
        limit=0,
        pattern="*",
        single=False,
        type=["wav"],
        convert="",
        target="",
        attributes="",
        query="",
        sort="",
        cwd="",
    )

    outputs = glob.glob(str(output_dir) + "/*")

    assert len(outputs) == 3

    for path in outputs:
        if path.endswith(".html"):
            with open(path) as f:
                assert f.readline().find("<!doctype html>") == 0
        if path.endswith(".csv"):
            with open(path) as f:
                assert csv.Sniffer().has_header(f.readline()) == True
        if path.endswith(".json"):
            with open(path) as f:
                assert list(json.loads(f.read()).keys()) == ["metadata", "log"]
