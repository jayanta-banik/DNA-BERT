from tokenizers import Tokenizer, models, pre_tokenizers, trainers

from .base import SPECIAL_TOKENS, ProteinTokenizer


class UnigramTokenizer(ProteinTokenizer):
    name = "Unigram"
    requires_training = True

    def train(self, protein_table, save_dir, vocab_size, batch_size=65536, total_batches=None):
        self.tokenizer = Tokenizer(models.Unigram())
        self.tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()

        trainer = trainers.UnigramTrainer(
            vocab_size=vocab_size,
            special_tokens=SPECIAL_TOKENS,
            unk_token="[UNK]",
        )

        self.tokenizer.train_from_iterator(
            iterator=self.iter_training_corpus(protein_table, batch_size=batch_size, total_batches=total_batches),
            trainer=trainer,
        )

        self._configure_postprocessing()
        self.save(save_dir)
        print(f"Vocab size learned: {self.tokenizer.get_vocab_size()}")
        return self
