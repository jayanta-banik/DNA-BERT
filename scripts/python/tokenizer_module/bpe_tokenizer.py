from tokenizers import Tokenizer, models, trainers

from .base import SPECIAL_TOKENS, ProteinTokenizer


class BPETokenizer(ProteinTokenizer):
    name = "BPE"
    requires_training = True

    def normalize(self, seq):
        return self.normalizer.normalize(seq, add_spaces=False)

    def train(self, protein_table, save_dir, vocab_size, min_frequency=2, batch_size=65536, **kwargs):
        print(
            f"[BPETokenizer.train] start vocab_size={vocab_size} min_frequency={min_frequency} batch_size={batch_size}",
            flush=True,
        )
        self.tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
        print("[BPETokenizer.train] tokenizer instance created", flush=True)

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=SPECIAL_TOKENS,
        )
        print("[BPETokenizer.train] trainer configured", flush=True)

        print("[BPETokenizer.train] train_from_iterator begin", flush=True)
        self.tokenizer.train_from_iterator(
            iterator=self.iter_training_corpus(protein_table, batch_size=batch_size),
            trainer=trainer,
        )
        print("[BPETokenizer.train] train_from_iterator done", flush=True)

        print("[BPETokenizer.train] postprocessing configuration begin", flush=True)
        self._configure_postprocessing()
        print("[BPETokenizer.train] postprocessing configuration done", flush=True)
        print(f"Vocab size learned: {self.tokenizer.get_vocab_size()}")
        return self
