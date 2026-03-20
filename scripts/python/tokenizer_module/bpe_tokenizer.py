from tokenizers import Tokenizer, models, trainers

from .base import SPECIAL_TOKENS, ProteinTokenizer


class BPETokenizer(ProteinTokenizer):
    name = "BPE"
    requires_training = True

    def normalize(self, seq):
        return self.normalizer.normalize(seq, add_spaces=False)

    def train(self, protein_table, save_dir, vocab_size, min_frequency=2, batch_size=65536, **kwargs):
        self.tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=SPECIAL_TOKENS,
        )

        self.tokenizer.train_from_iterator(
            iterator=self.iter_training_corpus(protein_table, batch_size=batch_size),
            trainer=trainer,
        )

        self._configure_postprocessing()
        self.save(save_dir)
        print(f"Vocab size learned: {self.tokenizer.get_vocab_size()}")
        return self
