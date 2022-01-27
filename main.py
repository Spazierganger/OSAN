import argparse
from argparse import Namespace
import os
import pickle

import torch
from torch.utils.tensorboard import SummaryWriter
from torch_geometric.datasets import TUDataset

from custom_dataloder import MYDataLoader
from models import NetGINE, NetGCN
from train import train, validation


def get_parse() -> Namespace:
    parser = argparse.ArgumentParser(description='GNN baselines')
    parser.add_argument('--model', type=str, default='gine')
    parser.add_argument('--dataset', type=str, default='zinc')
    parser.add_argument('--hid_size', type=int, default=256)
    parser.add_argument('--batch_size', type=int, default=8)
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--sample_k', type=int, default=15, help='top-k nodes, i.e. n_nodes of each subgraph')
    parser.add_argument('--num_subgraphs', type=int, default=3, help='number of subgraphs to sample for a graph')
    parser.add_argument('--data_path', type=str, default='./datasets')
    parser.add_argument('--log_path', type=str, default='./logs')

    return parser.parse_args()


if __name__ == '__main__':
    args = get_parse()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    if args.dataset.lower() == 'zinc':
        if not os.path.isdir(args.data_path):
            os.mkdir(args.data_path)
        dataset = TUDataset(args.data_path, name="ZINC_full")
    else:
        raise NotImplementedError

    if not os.path.isdir(args.log_path):
        os.mkdir(args.log_path)
    writer = SummaryWriter(args.log_path)

    # TODO: use full indices
    with open(os.path.join(args.data_path, 'indices', 'train_indices.pkl'), 'rb') as handle:
        train_indices = pickle.load(handle)[:32]

    with open(os.path.join(args.data_path, 'indices', 'test_indices.pkl'), 'rb') as handle:
        test_indices = pickle.load(handle)[:32]

    with open(os.path.join(args.data_path, 'indices', 'val_indices.pkl'), 'rb') as handle:
        val_indices = pickle.load(handle)[:32]

    # infile = open("./datasets/indices/test.index.txt", "r")
    # for line in infile:
    #     indices_test = line.split(",")
    #     indices_test = [int(i) for i in indices_test]
    #
    # infile = open("./datasets/indices/val.index.txt", "r")
    # for line in infile:
    #     indices_val = line.split(",")
    #     indices_val = [int(i) for i in indices_val]
    #
    # infile = open("./datasets/indices/train.index.txt", "r")
    # for line in infile:
    #     indices_train = line.split(",")
    #     indices_train = [int(i) for i in indices_train]

    train_loader = MYDataLoader(dataset[:220011][train_indices], batch_size=args.batch_size, shuffle=False,
                                n_subgraphs=0)
    test_loader = MYDataLoader(dataset[220011:225011][test_indices], batch_size=args.batch_size, shuffle=False,
                               n_subgraphs=0)
    val_loader = MYDataLoader(dataset[225011:][val_indices], batch_size=args.batch_size, shuffle=False, n_subgraphs=0)

    if args.model.lower() == 'gine':
        model = NetGINE(args.hid_size).to(device)
    else:
        raise NotImplementedError

    emb_model = NetGCN(28, args.hid_size, args.num_subgraphs).to(device)

    optimizer = torch.optim.Adam(list(emb_model.parameters()) + list(model.parameters()), lr=0.001)
    criterion = torch.nn.L1Loss()

    torch.save(emb_model.state_dict(), './model1.pt')
    for epoch in range(args.epochs):
        train_loss = train(args.sample_k, train_loader, emb_model, model, optimizer, criterion, device)
        val_loss = validation(args.sample_k, val_loader, emb_model, model, criterion, device)

        print(f'epoch: {epoch}, '
              f'training loss: {train_loss}, '
              f'val loss: {val_loss}')
        writer.add_scalar('loss/training loss', train_loss, epoch)
        writer.add_scalar('loss/val loss', val_loss, epoch)
    torch.save(emb_model.state_dict(), './model2.pt')
