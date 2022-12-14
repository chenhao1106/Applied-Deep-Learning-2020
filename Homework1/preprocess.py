import os
import argparse
import logging
import pickle
import json
from pathlib import Path
from tqdm import tqdm

from dataset import Seq2SeqDataset, SeqTaggingDataset
from utils import Tokenizer, Embeddings


def main(args):
    # Load embeddings.
    logging.info('Load embeddings...')
    embedding_path = './embedding.pkl'
    if not os.path.exists(embedding_path):
        embeddings = Embeddings(args.embeddings_file)
        with open(embedding_path, 'wb') as f:
            pickle.dump(embeddings, f)
    else:
        with open(embedding_path, 'rb') as f:
            embeddings = pickle.load(f)

    # Tokenize the data
    logging.info('Set up tokenizer...')
    tokenizer = Tokenizer(embeddings.vocab)

    # Create sequence tagging dataset.
    logging.info('Create dataset...')
    with open('./data/train.jsonl') as f:
        data = [json.loads(line) for line in f.readlines()]

    create_seq_tag_dataset(
        process_seq_tag_samples(tokenizer, data),
        './data/seq_tag_train_dataset.pkl',
        tokenizer.pad_token_idx
    )

    create_seq2seq_dataset(
        process_seq2seq_samples(tokenizer, data),
        './data/seq2seq_train_dataset.pkl',
        tokenizer.pad_token_idx
    )

    with open('./data/valid.jsonl') as f:
        data = [json.loads(line) for line in f.readlines()]

    create_seq_tag_dataset(
        process_seq_tag_samples(tokenizer, data),
        './data/seq_tag_valid_dataset.pkl',
        tokenizer.pad_token_idx
    )

    create_seq2seq_dataset(
        process_seq2seq_samples(tokenizer, data),
        './data/seq2seq_valid_dataset.pkl',
        tokenizer.pad_token_idx
    )

    with open('./data/test.jsonl') as f:
        data = [json.loads(line) for line in f.readlines()]

    create_seq_tag_dataset(
        process_seq_tag_samples(tokenizer, data),
        './data/seq_tag_test_dataset.pkl',
        tokenizer.pad_token_idx
    )

    create_seq2seq_dataset(
        process_seq2seq_samples(tokenizer, data),
        './data/seq2seq_test_dataset.pkl',
        tokenizer.pad_token_idx
    )


# Process sequence tagging task samples.
def process_seq_tag_samples(tokenizer, samples):
    processeds = []
    for sample in tqdm(samples):
        if not sample['sent_bounds']: continue

        processed = {
            'id': sample['id'],
            'text': tokenizer.encode(sample['text']),
            'sent_range': get_tokens_range(tokenizer, sample)
        }

        # Processing training or validating data.
        if 'extractive_summary' in sample:
            label_start, label_end = processed['sent_range'][sample['extractive_summary']]
            # Label of every tokens in summary is 1, 0 else.
            processed['label'] = [
                1 if label_start <= i < label_end else 0
                for i in range(len(processed['text']))
            ]
        processeds.append(processed)
    return processeds


# Transform character indices into token indices.
def get_tokens_range(tokenizer, sample):
    ranges = []
    token_start = 0
    for char_start, char_end in sample['sent_bounds']:
        sent = sample['text'][char_start:char_end]
        tokens_in_sent = tokenizer.tokenize(sent)
        token_end = token_start + len(tokens_in_sent)
        ranges.append([token_start, token_end])
        token_start = token_end
    return ranges


# Create sequence tagging task dataset.
def create_seq_tag_dataset(samples, save_path, padding=0):
    dataset = SeqTaggingDataset(
        samples, padding=padding,
        max_text_len=300
    )
    with open(save_path, 'wb') as f:
        pickle.dump(dataset, f)


# Process sequence to sequence task samples.
def process_seq2seq_samples(tokenizer, samples):
    bos_idx = tokenizer.bos_token_idx
    eos_idx = tokenizer.eos_token_idx
    processeds = []
    for sample in tqdm(samples):
        processed = {
            'id': sample['id'],
            'text': tokenizer.encode(sample['text']) + [eos_idx]
        }
        if 'summary' in sample:
            processed['summary'] =\
                [bos_idx] +\
                tokenizer.encode(sample['summary']) +\
                [eos_idx]
        processeds.append(processed)

    return processeds


# Create sequence to sequence task dataset.
def create_seq2seq_dataset(samples, save_path, padding=0):
    dataset = Seq2SeqDataset(
        samples, padding=padding,
        max_text_len=300,
        max_summary_len=80
    )
    with open(save_path, 'wb') as f:
        pickle.dump(dataset, f)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('embeddings_file', type=Path, help='path to the embeddings file')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s',
                        level='INFO', datefmt='%Y-%m-%d %H:%M:%S')
    main(args)
