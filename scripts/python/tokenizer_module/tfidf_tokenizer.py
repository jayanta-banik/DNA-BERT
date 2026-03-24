import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .base import RARE_RESIDUES, SPECIAL_TOKENS, STANDARD_RESIDUES, ProteinTokenizer

FORMAT_VERSION = "1.0"
INVALID_SYMBOL = "\0"


@dataclass
class TfidfEncoding:
    ids: list[int]
    tokens: list[str]


@dataclass
class CandidateTokenStat:
    token: str
    length: int
    tf: int = 0
    df: int = 0
    idf: float = 0.0
    complexity: float = 0.0
    length_bonus: float = 1.0
    score: float = 0.0
    is_low_complexity_filtered: bool = False


@dataclass
class VocabularyEntry:
    token: str
    token_id: int
    vocabulary_order: int
    token_type: str
    length: int
    tf: int = 0
    df: int = 0
    idf: float = 0.0
    complexity: float = 0.0
    score: float = 0.0


class _TfidfAdapter:
    def __init__(self, owner):
        self.owner = owner

    def encode(self, text):
        return self.owner._encode_tokens(text)

    def get_vocab(self):
        return dict(self.owner.vocab)

    def token_to_id(self, token):
        return self.owner.vocab[token]


class TfidfTokenizer(ProteinTokenizer):
    name = "TFIDF"
    requires_training = True

    def __init__(
        self,
        unk_token="[UNK]",
        special_tokens=None,
        standard_residues=None,
        rare_residues=None,
        rare_residue_policy="keep",
        fallback_residue="X",
        normalize=True,
        case_sensitive=False,
        min_k=2,
        max_k=6,
        min_tf=1,
        min_df=1,
        vocab_size=8000,
        tf_mode="log",
        idf_mode="smooth",
        scoring_mode="complexity_regularized_tfidf",
        alpha=0.1,
        filter_low_complexity=True,
        low_complexity_threshold=0.3,
        search_method="brute",
        beam_width=4,
        merge_strategy="accumulate",
        max_seq_length=512,
        **kwargs,
    ):
        super().__init__(max_seq_length=max_seq_length, rare_residue_policy=rare_residue_policy, **kwargs)
        self.unk_token = unk_token
        self.special_tokens = list(special_tokens or SPECIAL_TOKENS)
        self.standard_residues = set(standard_residues or STANDARD_RESIDUES)
        self.rare_residues = set(rare_residues or RARE_RESIDUES)
        self.fallback_residue = fallback_residue
        self.normalize_sequences = normalize
        self.case_sensitive = case_sensitive
        self.min_k = min_k
        self.max_k = max_k
        self.min_tf = min_tf
        self.min_df = min_df
        self.vocab_size = vocab_size
        self.tf_mode = tf_mode
        self.idf_mode = idf_mode
        self.scoring_mode = scoring_mode
        self.alpha = alpha
        self.filter_low_complexity = filter_low_complexity
        self.low_complexity_threshold = low_complexity_threshold
        self.search_method = search_method
        self.beam_width = beam_width
        self.merge_strategy = merge_strategy

        self.total_documents = 0
        self.total_shards = 0
        self.candidate_stats: dict[str, CandidateTokenStat] = {}
        self.vocabulary_entries: list[VocabularyEntry] = []
        self.vocab: dict[str, int] = {}
        self._search_index: dict[str, list[VocabularyEntry]] = {}

        self._validate_config()
        self.tokenizer = _TfidfAdapter(self)

    def normalize(self, seq):
        return "".join(symbol for symbol in self._normalize_symbols(seq, preserve_invalid=False) if symbol)

    def fit(self, file_path, mode="fresh"):
        mode = mode.lower()
        if mode not in {"fresh", "continue"}:
            raise ValueError("mode must be one of: fresh, continue")

        if mode == "continue" and not self.candidate_stats and self.total_documents == 0:
            raise ValueError("continue mode requires an already trained or loaded tokenizer state")

        shard_paths = self._resolve_shard_paths(file_path)
        new_stats, document_count, shard_count = self._scan_shards(shard_paths)

        if document_count == 0:
            raise ValueError("training corpus is empty after ignoring empty lines")

        if mode == "fresh":
            self._reset_training_state()
            self.total_documents = document_count
            self.total_shards = shard_count
            self.candidate_stats = new_stats
        else:
            self._merge_candidate_stats(new_stats)
            self.total_documents += document_count
            self.total_shards += shard_count

        previous_active_tokens = None
        if mode == "continue" and self.merge_strategy == "freeze_vocab":
            previous_active_tokens = {entry.token for entry in self.vocabulary_entries if entry.token_type == "learned"}

        self._rebuild_vocabulary(allowed_learned_tokens=previous_active_tokens)
        return self

    def continue_fit(self, file_path):
        return self.fit(file_path, mode="continue")

    def tokenize(self, sequence):
        self._ensure_trained()
        symbols = self._normalize_symbols(sequence, preserve_invalid=True)

        if self.search_method == "beam":
            return self._beam_tokenize(symbols)
        return self._brute_tokenize(symbols)

    def tokenize_file(self, input_path, output_path=None):
        self._ensure_trained()
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"input file does not exist: {input_path}")
        if input_path.is_dir():
            raise ValueError(f"tokenize_file expects a file path, got directory: {input_path}")

        tokenized_lines = []
        for raw_line in input_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            tokenized_lines.append(self.tokenize(raw_line))

        if output_path is not None:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            rendered = "\n".join(" ".join(tokens) for tokens in tokenized_lines)
            output_path.write_text(rendered + ("\n" if rendered else ""), encoding="utf-8")

        return tokenized_lines

    def encode(self, seq):
        self._ensure_trained()
        return self._encode_tokens(seq)

    def save(self, path):
        self._ensure_trained()
        path = Path(path)
        if path.suffix == ".json":
            target_path = path
            target_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
            target_path = path / "tokenizer_state.json"

        state = {
            "format_version": FORMAT_VERSION,
            "tokenizer_name": self.__class__.__name__,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "total_documents": self.total_documents,
            "total_shards": self.total_shards,
            "config": self._config_state(),
            "candidate_stats": {token: asdict(stat) for token, stat in sorted(self.candidate_stats.items())},
            "vocabulary": [asdict(entry) for entry in self.vocabulary_entries],
        }
        target_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return target_path

    @classmethod
    def load(cls, path):
        path = Path(path)
        state_path = path / "tokenizer_state.json" if path.is_dir() else path
        if not state_path.exists():
            raise FileNotFoundError(f"tokenizer state file does not exist: {state_path}")

        state = json.loads(state_path.read_text(encoding="utf-8"))
        config = dict(state["config"])
        tokenizer = cls(**config)
        tokenizer.total_documents = state["total_documents"]
        tokenizer.total_shards = state.get("total_shards", 0)
        tokenizer.candidate_stats = {token: CandidateTokenStat(**payload) for token, payload in state.get("candidate_stats", {}).items()}
        vocabulary = [VocabularyEntry(**entry) for entry in state.get("vocabulary", [])]
        tokenizer._restore_vocabulary(vocabulary)
        return tokenizer

    def _encode_tokens(self, sequence):
        tokens = self.tokenize(sequence)
        ids = [self.vocab.get(token, self.vocab[self.unk_token]) for token in tokens]
        return TfidfEncoding(ids=ids, tokens=tokens)

    def _reset_training_state(self):
        self.total_documents = 0
        self.total_shards = 0
        self.candidate_stats = {}
        self.vocabulary_entries = []
        self.vocab = {}
        self._search_index = {}
        self.tokenizer = _TfidfAdapter(self)

    def _validate_config(self):
        if self.min_k < 1:
            raise ValueError("min_k must be >= 1")
        if self.max_k < self.min_k:
            raise ValueError("max_k must be >= min_k")
        if self.vocab_size < 1:
            raise ValueError("vocab_size must be >= 1")
        if self.min_tf < 1 or self.min_df < 1:
            raise ValueError("min_tf and min_df must both be >= 1")
        if not 0.0 <= self.low_complexity_threshold <= 1.0:
            raise ValueError("low_complexity_threshold must be within [0.0, 1.0]")
        if self.tf_mode not in {"raw", "log"}:
            raise ValueError("tf_mode must be one of: raw, log")
        if self.idf_mode not in {"standard", "smooth", "probabilistic"}:
            raise ValueError("idf_mode must be one of: standard, smooth, probabilistic")
        if self.scoring_mode not in {"tfidf", "log_tfidf", "complexity_regularized_tfidf"}:
            raise ValueError("scoring_mode must be one of: tfidf, log_tfidf, complexity_regularized_tfidf")
        if self.search_method not in {"brute", "beam"}:
            raise ValueError("search_method must be one of: brute, beam")
        if self.search_method == "beam" and self.beam_width < 1:
            raise ValueError("beam_width must be >= 1 when search_method is beam")
        if self.merge_strategy not in {"accumulate", "replace_vocab", "freeze_vocab"}:
            raise ValueError("merge_strategy must be one of: accumulate, replace_vocab, freeze_vocab")
        if self.rare_residue_policy not in {"keep", "replace_with_unk", "replace_with_nn"}:
            raise ValueError("rare_residue_policy must be one of: keep, replace_with_unk, replace_with_nn")
        if not self.special_tokens:
            raise ValueError("special_tokens must contain at least one token")
        if self.unk_token not in self.special_tokens:
            self.special_tokens.append(self.unk_token)
        if len(self.fallback_residue) != 1:
            raise ValueError("fallback_residue must be a single character")

    def _ensure_trained(self):
        if not self.vocabulary_entries:
            raise ValueError("tokenizer has not been trained or loaded")

    def _config_state(self):
        return {
            "unk_token": self.unk_token,
            "special_tokens": list(self.special_tokens),
            "standard_residues": sorted(self.standard_residues),
            "rare_residues": sorted(self.rare_residues),
            "rare_residue_policy": self.rare_residue_policy,
            "fallback_residue": self.fallback_residue,
            "normalize": self.normalize_sequences,
            "case_sensitive": self.case_sensitive,
            "min_k": self.min_k,
            "max_k": self.max_k,
            "min_tf": self.min_tf,
            "min_df": self.min_df,
            "vocab_size": self.vocab_size,
            "tf_mode": self.tf_mode,
            "idf_mode": self.idf_mode,
            "scoring_mode": self.scoring_mode,
            "alpha": self.alpha,
            "filter_low_complexity": self.filter_low_complexity,
            "low_complexity_threshold": self.low_complexity_threshold,
            "search_method": self.search_method,
            "beam_width": self.beam_width,
            "merge_strategy": self.merge_strategy,
            "max_seq_length": self.max_seq_length,
        }

    def _resolve_shard_paths(self, file_path):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"training path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() != ".txt":
                raise ValueError(f"training file must be a .txt shard: {path}")
            return [path]

        shard_paths = sorted(child for child in path.iterdir() if child.is_file() and child.suffix.lower() == ".txt")
        if not shard_paths:
            raise ValueError(f"training folder contains no .txt shard files: {path}")
        return shard_paths

    def _scan_shards(self, shard_paths):
        aggregated_stats = {}
        document_count = 0

        for shard_path in shard_paths:
            for raw_line in shard_path.read_text(encoding="utf-8").splitlines():
                if not raw_line.strip():
                    continue
                document_count += 1
                seen_in_document = set()
                for span in self._normalized_training_spans(raw_line):
                    if not span:
                        continue
                    for token in self._iter_substrings(span):
                        stat = aggregated_stats.get(token)
                        if stat is None:
                            stat = CandidateTokenStat(token=token, length=len(token))
                            aggregated_stats[token] = stat
                        stat.tf += 1
                        seen_in_document.add(token)

                for token in seen_in_document:
                    aggregated_stats[token].df += 1

        return aggregated_stats, document_count, len(shard_paths)

    def _merge_candidate_stats(self, new_stats):
        for token, incoming in new_stats.items():
            existing = self.candidate_stats.get(token)
            if existing is None:
                self.candidate_stats[token] = CandidateTokenStat(token=token, length=incoming.length, tf=incoming.tf, df=incoming.df)
                continue
            existing.tf += incoming.tf
            existing.df += incoming.df

    def _normalized_training_spans(self, sequence):
        symbols = self._normalize_symbols(sequence, preserve_invalid=True)
        spans = []
        current = []
        for symbol in symbols:
            if symbol == INVALID_SYMBOL:
                if current:
                    spans.append("".join(current))
                    current = []
                continue
            current.append(symbol)
        if current:
            spans.append("".join(current))
        return spans

    def _normalize_symbols(self, sequence, preserve_invalid):
        if sequence is None:
            sequence = ""
        if not isinstance(sequence, str):
            sequence = str(sequence)

        normalized = sequence.strip()
        if not self.case_sensitive:
            normalized = normalized.upper()
        if self.normalize_sequences:
            normalized = "".join(normalized.split())

        symbols = []
        for char in normalized:
            if char in self.standard_residues:
                symbols.append(char)
            elif char in self.rare_residues:
                if self.rare_residue_policy == "keep":
                    symbols.append(char)
                elif self.rare_residue_policy == "replace_with_unk":
                    if preserve_invalid:
                        symbols.append(INVALID_SYMBOL)
                else:
                    symbols.append(self.fallback_residue)
            elif preserve_invalid:
                symbols.append(INVALID_SYMBOL)

        return symbols

    def _iter_substrings(self, normalized_span):
        if not normalized_span:
            return
        upper_k = min(self.max_k, len(normalized_span))
        for k in range(self.min_k, upper_k + 1):
            for start in range(0, len(normalized_span) - k + 1):
                yield normalized_span[start : start + k]

    def _rebuild_vocabulary(self, allowed_learned_tokens=None):
        ranked_candidates = []
        for token, stat in self.candidate_stats.items():
            self._update_scored_stat(stat)
            if stat.tf < self.min_tf or stat.df < self.min_df:
                continue
            if self.filter_low_complexity and stat.complexity < self.low_complexity_threshold:
                stat.is_low_complexity_filtered = True
                continue
            stat.is_low_complexity_filtered = False
            if allowed_learned_tokens is not None and token not in allowed_learned_tokens:
                continue
            ranked_candidates.append(stat)

        ranked_candidates.sort(key=lambda stat: (-stat.score, -stat.length, stat.token))
        learned_candidates = ranked_candidates[: self.vocab_size]

        entries = []
        seen_tokens = set()
        mandatory_single_chars = sorted(self.standard_residues | self.rare_residues | {self.fallback_residue})

        for token in list(dict.fromkeys(self.special_tokens + [self.unk_token])):
            entry = self._entry_for_token(token, token_type="special")
            entries.append(entry)
            seen_tokens.add(token)

        for token in mandatory_single_chars:
            if token in seen_tokens:
                continue
            entry = self._entry_for_token(token, token_type="single_character")
            entries.append(entry)
            seen_tokens.add(token)

        for stat in learned_candidates:
            if stat.token in seen_tokens:
                continue
            entry = self._entry_for_token(stat.token, token_type="learned")
            entries.append(entry)
            seen_tokens.add(stat.token)

        self._restore_vocabulary(entries)

    def _restore_vocabulary(self, entries):
        restored_entries = []
        vocab = {}
        for order, entry in enumerate(entries):
            normalized_entry = VocabularyEntry(
                token=entry.token,
                token_id=order,
                vocabulary_order=order,
                token_type=entry.token_type,
                length=entry.length,
                tf=entry.tf,
                df=entry.df,
                idf=entry.idf,
                complexity=entry.complexity,
                score=entry.score,
            )
            restored_entries.append(normalized_entry)
            vocab[normalized_entry.token] = normalized_entry.token_id

        self.vocabulary_entries = restored_entries
        self.vocab = vocab
        self.tokenizer = _TfidfAdapter(self)
        self._rebuild_search_index()

    def _rebuild_search_index(self):
        search_index = defaultdict(list)
        for entry in self.vocabulary_entries:
            if entry.token_type == "special" or entry.token == self.unk_token:
                continue
            search_index[entry.token[0]].append(entry)

        for token_group in search_index.values():
            token_group.sort(key=lambda entry: (-entry.score, -entry.length, entry.vocabulary_order))

        self._search_index = dict(search_index)

    def _entry_for_token(self, token, token_type):
        stat = self.candidate_stats.get(token)
        if stat is None:
            complexity = 1.0 if len(token) == 1 else self._complexity(token)
            return VocabularyEntry(
                token=token,
                token_id=-1,
                vocabulary_order=-1,
                token_type=token_type,
                length=len(token),
                tf=0,
                df=0,
                idf=0.0,
                complexity=complexity,
                score=0.0,
            )

        return VocabularyEntry(
            token=token,
            token_id=-1,
            vocabulary_order=-1,
            token_type=token_type,
            length=stat.length,
            tf=stat.tf,
            df=stat.df,
            idf=stat.idf,
            complexity=stat.complexity,
            score=stat.score,
        )

    def _update_scored_stat(self, stat):
        stat.length = len(stat.token)
        stat.complexity = self._complexity(stat.token)
        stat.length_bonus = 1 + (self.alpha * max(stat.length - self.min_k, 0))
        stat.idf = self._idf_value(stat.df)
        stat.score = self._score_value(stat)

    def _complexity(self, token):
        if not token:
            return 0.0
        return len(set(token)) / len(token)

    def _tf_value(self, tf):
        if self.tf_mode == "raw":
            return float(tf)
        return math.log1p(tf)

    def _idf_value(self, df):
        if df <= 0 or self.total_documents <= 0:
            return 0.0
        if self.idf_mode == "standard":
            return math.log(self.total_documents / df)
        if self.idf_mode == "smooth":
            return math.log((self.total_documents + 1) / (df + 1)) + 1

        remaining_documents = self.total_documents - df
        if remaining_documents <= 0:
            return 0.0
        return math.log(remaining_documents / df)

    def _score_value(self, stat):
        if self.scoring_mode == "tfidf":
            return self._tf_value(stat.tf) * stat.idf
        if self.scoring_mode == "log_tfidf":
            return math.log1p(stat.tf) * stat.idf
        return self._tf_value(stat.tf) * stat.idf * stat.complexity * stat.length_bonus

    def _brute_tokenize(self, symbols):
        tokens = []
        position = 0
        while position < len(symbols):
            entry = self._best_match(symbols, position)
            tokens.append(entry.token)
            position += max(entry.length, 1)
        return tokens

    def _beam_tokenize(self, symbols):
        beam = [(0, [], 0.0)]
        while beam:
            next_beam = []
            completed = []
            for position, tokens, score in beam:
                if position >= len(symbols):
                    completed.append((position, tokens, score))
                    continue
                for entry in self._matching_entries(symbols, position):
                    next_beam.append((position + max(entry.length, 1), tokens + [entry.token], score + entry.score))

            if completed and not next_beam:
                beam = completed
                break

            next_beam.sort(key=lambda item: (-item[2], len(item[1]), tuple(item[1])))
            beam = next_beam[: self.beam_width]

            if all(position >= len(symbols) for position, _, _ in beam):
                break

        best_position, best_tokens, _ = max(
            beam,
            key=lambda item: (item[0], item[2], -len(item[1]), tuple(item[1])),
        )
        if best_position < len(symbols):
            best_tokens.extend(self._brute_tokenize(symbols[best_position:]))
        return best_tokens

    def _best_match(self, symbols, position):
        matches = self._matching_entries(symbols, position)
        return matches[0]

    def _matching_entries(self, symbols, position):
        symbol = symbols[position]
        if symbol == INVALID_SYMBOL:
            return [
                VocabularyEntry(
                    token=self.unk_token,
                    token_id=self.vocab[self.unk_token],
                    vocabulary_order=self.vocab[self.unk_token],
                    token_type="special",
                    length=1,
                    tf=0,
                    df=0,
                    idf=0.0,
                    complexity=0.0,
                    score=0.0,
                )
            ]

        candidates = []
        for entry in self._search_index.get(symbol, []):
            if position + entry.length > len(symbols):
                continue
            if INVALID_SYMBOL in symbols[position : position + entry.length]:
                continue
            if entry.token == "".join(symbols[position : position + entry.length]):
                candidates.append(entry)

        if candidates:
            return candidates

        fallback_token = symbol if symbol in self.vocab else self.unk_token
        fallback_id = self.vocab.get(fallback_token, self.vocab[self.unk_token])
        fallback_entry = VocabularyEntry(
            token=fallback_token,
            token_id=fallback_id,
            vocabulary_order=fallback_id,
            token_type="single_character" if fallback_token != self.unk_token else "special",
            length=1,
            tf=0,
            df=0,
            idf=0.0,
            complexity=1.0 if fallback_token != self.unk_token else 0.0,
            score=0.0,
        )
        return [fallback_entry]
