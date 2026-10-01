from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf

from voxshield.data.ingest import SourceSpec, ingest_sources


def _write_tone(path: Path, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    time = np.arange(sample_rate // 10, dtype=np.float32) / sample_rate
    sf.write(path, 0.1 * np.sin(2.0 * np.pi * 440.0 * time), sample_rate)


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_ingest_references_known_and_explicit_sources_without_copying(tmp_path: Path) -> None:
    librispeech = tmp_path / "LibriSpeech"
    train_clean = librispeech / "train-clean-100" / "123" / "456" / "123-456-1.flac"
    val_clean = librispeech / "dev-clean" / "999" / "1" / "999-1-1.flac"
    _write_tone(train_clean)
    _write_tone(val_clean)

    impacts = tmp_path / "field-impacts" / "train"
    impact = impacts / "metal-hit.wav"
    _write_tone(impact)

    data_root = tmp_path / "project-data"
    counts = ingest_sources(
        [
            SourceSpec(librispeech),
            SourceSpec(impacts.parent, kind="noise", category="impulsive"),
        ],
        data_root,
    )

    clean_train = _rows(data_root / "manifests" / "clean_train.jsonl")
    clean_val = _rows(data_root / "manifests" / "clean_val.jsonl")
    noise_train = _rows(data_root / "manifests" / "noise_impulsive_train.jsonl")

    assert clean_train[0]["path"] == str(train_clean.resolve())
    assert clean_val[0]["path"] == str(val_clean.resolve())
    assert noise_train[0]["path"] == str(impact.resolve())
    assert counts["clean/train"] == 1
    assert counts["clean/val"] == 1
    assert counts["noise/impulsive/train"] == 1
    assert not (data_root / "raw").exists()
    assert len(_rows(data_root / "manifests" / "catalog.jsonl")) == 3


def test_ingest_vctk_and_mad_adapters_use_speaker_groups_and_csv_labels(tmp_path: Path) -> None:
    vctk = tmp_path / "VCTK-Corpus"
    vctk_audio = vctk / "wav48_silence_trimmed" / "p225" / "p225_001_mic1.flac"
    _write_tone(vctk_audio)
    # A second rendered tree must not duplicate the preferred silence-trimmed audio.
    _write_tone(vctk / "wav48" / "p225" / "p225_001.wav")

    mad = tmp_path / "MAD_dataset"
    gunshot = mad / "training" / "398" / "0.wav"
    communication = mad / "training" / "398" / "1.wav"
    helicopter = mad / "test" / "500" / "0.wav"
    for path in (gunshot, communication, helicopter):
        _write_tone(path)
    (mad / "training.csv").write_text(
        ",path,label,youtube title,youtube url\n"
        "0,training/398/0.wav,1,gunshot,https://example.invalid/a\n"
        "1,training/398/1.wav,0,communication,https://example.invalid/a\n",
        encoding="utf-8",
    )
    (mad / "test.csv").write_text(
        ",path,label,youtube title,youtube url\n"
        "0,test/500/0.wav,5,helicopter,https://example.invalid/b\n",
        encoding="utf-8",
    )

    data_root = tmp_path / "data"
    counts = ingest_sources([SourceSpec(vctk), SourceSpec(mad)], data_root)
    catalog = _rows(data_root / "manifests" / "catalog.jsonl")
    vctk_rows = [row for row in catalog if row["adapter"] == "vctk"]
    mad_rows = [row for row in catalog if row["adapter"] == "mad"]

    assert len(vctk_rows) == 1
    assert vctk_rows[0]["kind"] == "clean"
    assert vctk_rows[0]["group"] == "p225"
    assert {row["source_label"] for row in mad_rows} == {"gunshot", "helicopter"}
    assert {row["category"] for row in mad_rows} == {"impulsive", "nonstationary"}
    assert {row["split"] for row in mad_rows} == {"train", "test"}
    assert counts["skipped"] == 1


def test_ingest_esc50_accepts_root_level_metadata_csv(tmp_path: Path) -> None:
    esc50 = tmp_path / "esc-50"
    audio = esc50 / "audio" / "4-example.wav"
    _write_tone(audio)
    (esc50 / "esc50.csv").write_text(
        "filename,fold,target,category,esc10,src_file,take\n"
        "4-example.wav,4,22,clapping,False,example,A\n",
        encoding="utf-8",
    )

    data_root = tmp_path / "data"
    ingest_sources([SourceSpec(esc50)], data_root)
    rows = _rows(data_root / "manifests" / "noise_impulsive_val.jsonl")

    assert len(rows) == 1
    assert rows[0]["adapter"] == "esc50"
    assert rows[0]["category_method"] == "esc50-metadata"
    assert rows[0]["split_method"] == "official/path"


def test_ingest_esc50_prefers_one_16khz_render(tmp_path: Path) -> None:
    esc50 = tmp_path / "esc-50"
    for directory, sample_rate in (
        (esc50 / "audio" / "audio", 44100),
        (esc50 / "audio" / "audio" / "44100", 44100),
        (esc50 / "audio" / "audio" / "16000", 16000),
    ):
        _write_tone(directory / "1-example.wav", sample_rate)
    (esc50 / "esc50.csv").write_text(
        "filename,fold,target,category,esc10,src_file,take\n"
        "1-example.wav,1,22,clapping,False,example,A\n",
        encoding="utf-8",
    )

    data_root = tmp_path / "data"
    ingest_sources([SourceSpec(esc50)], data_root, scan_workers=2)
    rows = _rows(data_root / "manifests" / "catalog.jsonl")

    assert len(rows) == 1
    assert rows[0]["sample_rate"] == 16000
    assert "16000" in str(rows[0]["path"])
