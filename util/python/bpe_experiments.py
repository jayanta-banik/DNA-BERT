from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable


def _require_sentencepiece():
    try:
        import sentencepiece as spm  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError("sentencepiece is required for BPE comparison. Install it in ~/venv3 before running the BPE notebook cells.") from exc
    return spm


def train_bpe_model(
    sequences: Iterable[str],
    vocab_size: int,
    model_prefix: str,
    model_dir: str | Path,
) -> Path:
    spm = _require_sentencepiece()
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = model_dir / f"{model_prefix}.txt"
    corpus_path.write_text("\n".join(sequences), encoding="utf-8")
    prefix_path = model_dir / model_prefix
    spm.SentencePieceTrainer.train(
        input=str(corpus_path),
        model_prefix=str(prefix_path),
        vocab_size=vocab_size,
        model_type="bpe",
        bos_id=-1,
        eos_id=-1,
        pad_id=-1,
        unk_piece="[UNK]",
    )
    return prefix_path.with_suffix(".model")


def tokenize_with_bpe(sequences: Iterable[str], model_path: str | Path) -> list[list[str]]:
    spm = _require_sentencepiece()
    processor = spm.SentencePieceProcessor(model_file=str(model_path))
    return [processor.encode(sequence, out_type=str) for sequence in sequences]


def evaluate_bpe_vocab_grid(
    sequences: Iterable[str],
    vocab_sizes: Iterable[int],
    model_dir: str | Path,
) -> dict[str, list[list[str]]]:
    cached_sequences = list(sequences)
    outputs: dict[str, list[list[str]]] = {}
    for vocab_size in vocab_sizes:
        model_path = train_bpe_model(
            sequences=cached_sequences,
            vocab_size=vocab_size,
            model_prefix=f"bpe_{vocab_size}",
            model_dir=model_dir,
        )
        outputs[f"bpe_{vocab_size}"] = tokenize_with_bpe(cached_sequences, model_path)
    return outputs


def evaluate_bpe_with_tempdir(sequences: Iterable[str], vocab_sizes: Iterable[int]) -> dict[str, list[list[str]]]:
    with TemporaryDirectory() as temporary_dir:
        return evaluate_bpe_vocab_grid(sequences=sequences, vocab_sizes=vocab_sizes, model_dir=temporary_dir)
