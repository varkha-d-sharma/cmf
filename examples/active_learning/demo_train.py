import argparse
import numpy as np
import torch
from utils import get_dataset, get_net, get_strategy, get_trained_net
from pprint import pprint
from cmflib import cmf
from linear_regression import LinearPredictor
import matplotlib.pyplot as plt
import matplotlib

#matplotlib.use('Agg')
parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=1, help="random seed")
parser.add_argument('--n_init_labeled', type=int, default=10000, help="number of init labeled samples")
parser.add_argument('--n_query', type=int, default=10, help="number of queries per round")
parser.add_argument('--n_round', type=int, default=10, help="number of rounds")
parser.add_argument('--dataset_name', type=str, default="MNIST", choices=["MNIST", "FashionMNIST", "SVHN", "CIFAR10"], help="dataset")
parser.add_argument('--enable_df', type=bool, default=False, help="Enable df")
parser.add_argument('--df_strategy_weight', type=float, default=0.5, help="weight of the strategy")
parser.add_argument('--df_pipeline_name', type=str, default="active-learning-single-strategy", help="Strategy datafoundation") 
parser.add_argument('--df_strategy_name', type=str, default="KMeansSampling", help="Strategy datafoundation") 
parser.add_argument('--round', type=int, default=1, help="round")
parser.add_argument('--trained_model', type=str, default="model", help="path of trained model")
parser.add_argument('--query_idx', type=str, default="query_idx", help="path to query idx")
parser.add_argument('--strategy_name', type=str, default="EntropySampling", 
                    choices=["RandomSampling", 
                             "LeastConfidence", 
                             "MarginSampling", 
                             "EntropySampling", 
                             "LeastConfidenceDropout", 
                             "MarginSamplingDropout", 
                             "EntropySamplingDropout", 
                             "KMeansSampling",
                             "KCenterGreedy", 
                             "BALDDropout", 
                             "AdversarialBIM", 
                             "AdversarialDeepFool"], help="query strategy")
args = parser.parse_args()
pprint(vars(args))
print()
rd = args.round

prev_model = args.trained_model

query_idxs_file = args.query_idx

np_query_idxs = np.loadtxt(query_idxs_file).astype(int)
query_idxs = torch.from_numpy(np_query_idxs)
# fix random seed
np.random.seed(args.seed)
torch.manual_seed(args.seed)
torch.backends.cudnn.enabled = False

# device
use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")

dataset = get_dataset(args.dataset_name)                   # load dataset

original_folder_path = "data/"+args.dataset_name

net = get_trained_net(args.dataset_name, device, prev_model)                   # load network
strategy = get_strategy(args.strategy_name)(dataset, net)  # load strategy
strategy_df = get_strategy(args.df_strategy_name)(dataset, net)
# start experiment
dataset.initialize_labels(args.n_init_labeled)
print(f"number of labeled pool: {args.n_init_labeled}")
print(f"number of unlabeled pool: {dataset.n_pool-args.n_init_labeled}")
print(f"number of testing pool: {dataset.n_test}")
print()

strategy.update(query_idxs)
strategy.train()

    #saving the model
model_path = "data/model-" + str(rd)
strategy.save_model(model_path)
