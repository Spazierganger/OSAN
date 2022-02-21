import os
from typing import Tuple, Optional, List, Dict, Mapping
from argparse import Namespace

from torch_geometric.datasets import TUDataset

from data.custom_dataloader import MYDataLoader
from data.subgraph_policy import policy2transform, DeckSampler, RawSampler
from data.custom_datasets import CustomTUDataset


def get_data(args: Namespace) -> Tuple[MYDataLoader, MYDataLoader, Optional[MYDataLoader]]:
    """

    :param args
    :return:
    """

    if args.dataset.lower() == 'zinc':
        if not os.path.isdir(args.data_path):
            os.mkdir(args.data_path)

        pre_transform = policy2transform(args.policy)

        if pre_transform is None:   # I-MLE, or normal training, or sample on the fly
            transform = None
            if (not args.train_embd_model) and (args.num_subgraphs > 0):   # sample-on-the-fly
                transform = RawSampler(args.num_subgraphs, args.sample_k)
            dataset = TUDataset(args.data_path, transform=transform, name="ZINC_full")
        else:   # ESAN: sample from the deck
            transform = DeckSampler(args.sample_mode, args.esan_frac, args.esan_k)
            dataset = CustomTUDataset(args.data_path + '/deck', name="ZINC_full",
                                      transform=transform, pre_transform=pre_transform)

        # infile = open("./datasets/indices/test.index.txt", "r")
        # for line in infile:
        #     test_indices = line.split(",")
        #     if debug:
        #         test_indices = test_indices[:16]
        #     test_indices = [int(i) for i in test_indices]

        infile = open("./datasets/indices/val.index.txt", "r")
        for line in infile:
            val_indices = line.split(",")
            if args.debug:
                val_indices = val_indices[:16]
            val_indices = [int(i) for i in val_indices]

        infile = open("./datasets/indices/train.index.txt", "r")
        for line in infile:
            train_indices = line.split(",")
            if args.debug:
                train_indices = train_indices[:16]
            train_indices = [int(i) for i in train_indices]

        # use subgraph collator when sample from deck or a graph
        # either case the batch will be [[g11, g12, g13], [g21, g22, g23], ...]
        sample_collator = (pre_transform is not None) or ((not args.train_embd_model) and (args.num_subgraphs > 0))

        train_loader = MYDataLoader(dataset[:220011][train_indices], batch_size=args.batch_size, shuffle=True,
                                    subgraph_loader=sample_collator)
        # test_loader = MYDataLoader(dataset[220011:225011][test_indices], batch_size=batch_size, shuffle=False,
        #                            subgraph_loader=pre_transform is not None)
        val_loader = MYDataLoader(dataset[225011:][val_indices], batch_size=args.batch_size, shuffle=False,
                                  subgraph_loader=sample_collator)
    else:
        raise NotImplementedError

    return train_loader, val_loader, None
