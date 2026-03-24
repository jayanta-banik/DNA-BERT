import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import sentencepiece as spm

from .base import SPECIAL_TOKENS, ProteinTokenizer


class LiveLogger:
    def write(self, msg):
        sys.stdout.write(msg)
        sys.stdout.flush()

    def flush(self):
        sys.stdout.flush()


@dataclass
class SentencePieceEncoding:
    ids: list[int]
    tokens: list[str]


class _SentencePieceAdapter:
    def __init__(self, processor, max_seq_length):
        self.processor = processor
        self.max_seq_length = max_seq_length

    def encode(self, text):
        cls_id = self.token_to_id("[CLS]")
        sep_id = self.token_to_id("[SEP]")
        pad_id = self.token_to_id("[PAD]")

        piece_ids = self.processor.encode(text, out_type=int)
        content_length = max(self.max_seq_length - 2, 0)
        piece_ids = piece_ids[:content_length]
        ids = [cls_id, *piece_ids, sep_id]

        if len(ids) < self.max_seq_length:
            ids.extend([pad_id] * (self.max_seq_length - len(ids)))
        else:
            ids = ids[: self.max_seq_length]
            if ids:
                ids[-1] = sep_id

        return SentencePieceEncoding(ids=ids, tokens=[self.processor.id_to_piece(idx) for idx in ids])

    def token_to_id(self, token):
        return self.processor.piece_to_id(token)

    def get_vocab(self):
        return {self.processor.id_to_piece(idx): idx for idx in range(self.processor.get_piece_size())}


class SentencePieceTokenizer(ProteinTokenizer):
    name = "SentencePiece"
    requires_training = True

    def __init__(self, model_type="bpe", character_coverage=1.0, **kwargs):
        super().__init__(**kwargs)
        self.model_type = model_type
        self.character_coverage = character_coverage
        self.model_path = None
        self.vocab_path = None
        self.processor = None
        print(f"Initialized {self.name} tokenizer with model_type={model_type} character_coverage={character_coverage}")

    def train(
        self,
        protein_table,
        save_dir,
        vocab_size,
        batch_size=65536,
        lines_per_corpus_file=50000,
        overwrite_corpus=False,
        input_sentence_size=0,
        shuffle_input_sentence=True,
        verbose=True,
        **kwargs,
    ):
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        print(f"[SentencePieceTokenizer.train] start vocab_size={vocab_size} model_type={self.model_type} batch_size={batch_size}")
        corpus_files = self.write_normalized_corpus(
            protein_dataset=protein_table,
            save_dir=save_dir,
            batch_size=batch_size,
            lines_per_file=lines_per_corpus_file,
            overwrite=overwrite_corpus,
        )
        print(f"[SentencePieceTokenizer.train] corpus ready ({len(corpus_files)} files)")

        model_prefix = save_dir / "sentencepiece"
        for artifact_path in (model_prefix.with_suffix(".model"), model_prefix.with_suffix(".vocab")):
            if artifact_path.exists():
                artifact_path.unlink()

        train_kwargs = {
            "input": ",".join(str(path) for path in corpus_files),
            "model_prefix": str(model_prefix),
            "model_type": self.model_type,
            "vocab_size": vocab_size,
            "character_coverage": self.character_coverage,
            "normalization_rule_name": "identity",
            "hard_vocab_limit": False,
            "split_by_whitespace": False,
            "shuffle_input_sentence": shuffle_input_sentence,
            "pad_id": SPECIAL_TOKENS.index("[PAD]"),
            "unk_id": SPECIAL_TOKENS.index("[UNK]"),
            "bos_id": SPECIAL_TOKENS.index("[CLS]"),
            "eos_id": SPECIAL_TOKENS.index("[SEP]"),
            "pad_piece": "[PAD]",
            "unk_piece": "[UNK]",
            "bos_piece": "[CLS]",
            "eos_piece": "[SEP]",
            "user_defined_symbols": ["[MASK]", "[UNKAA]"],
        }

        if input_sentence_size:
            train_kwargs["input_sentence_size"] = input_sentence_size

        print("[SentencePieceTokenizer.train] model training begin")
        if verbose:
            with open("spm_train.log", "w") as f:
                spm.SentencePieceTrainer.train(**train_kwargs, logstream=f)
        else:
            spm.SentencePieceTrainer.train(**train_kwargs)
        print("[SentencePieceTokenizer.train] model training done")

        self._load_processor(model_prefix.with_suffix(".model"))
        print(f"Vocab size learned: {self.processor.get_piece_size()}")
        return self

    def save(self, save_dir):
        if self.model_path is None or not self.model_path.exists():
            raise ValueError("SentencePiece model is not available to save")

        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        model_target = save_dir / "sentencepiece.model"
        vocab_target = save_dir / "sentencepiece.vocab"
        meta_target = save_dir / "sentencepiece_meta.json"

        if self.model_path.resolve() != model_target.resolve():
            shutil.copy2(self.model_path, model_target)
        if self.vocab_path and self.vocab_path.exists() and self.vocab_path.resolve() != vocab_target.resolve():
            shutil.copy2(self.vocab_path, vocab_target)

        meta_target.write_text(
            json.dumps(
                {
                    "model_type": self.model_type,
                    "character_coverage": self.character_coverage,
                    "max_seq_length": self.max_seq_length,
                    "rare_residue_policy": self.rare_residue_policy,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Saved {self.name} tokenizer to: {model_target}")
        return model_target

    def load(self, path):
        path = Path(path)
        if path.is_dir():
            model_path = path / "sentencepiece.model"
            meta_path = path / "sentencepiece_meta.json"
        else:
            model_path = path
            meta_path = path.parent / "sentencepiece_meta.json"

        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.model_type = meta.get("model_type", self.model_type)
            self.character_coverage = meta.get("character_coverage", self.character_coverage)
            self.max_seq_length = meta.get("max_seq_length", self.max_seq_length)
            self.rare_residue_policy = meta.get("rare_residue_policy", self.rare_residue_policy)

        self._load_processor(model_path)
        return self

    def _load_processor(self, model_path):
        model_path = Path(model_path)
        processor = spm.SentencePieceProcessor(model_file=str(model_path))

        self.processor = processor
        self.model_path = model_path
        self.vocab_path = model_path.with_suffix(".vocab")
        self.tokenizer = _SentencePieceAdapter(processor=processor, max_seq_length=self.max_seq_length)
