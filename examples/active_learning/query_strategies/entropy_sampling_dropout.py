import numpy as np
import torch
from .strategy import Strategy

class EntropySamplingDropout(Strategy):
    def __init__(self, dataset, net, n_drop=10):
        super(EntropySamplingDropout, self).__init__(dataset, net)
        self.n_drop = n_drop

    def query(self, n):
        unlabeled_idxs, unlabeled_data = self.dataset.get_unlabeled_data()
        probs = self.predict_prob_dropout(unlabeled_data, n_drop=self.n_drop)
        log_probs = torch.log(probs)
        uncertainties = (probs*log_probs).sum(1)
        return unlabeled_idxs[uncertainties.sort()[1][:n]]

    def query_probs(self, n):
        unlabeled_idxs, unlabeled_data = self.dataset.get_unlabeled_data_subset(0.1)
        probs = self.predict_prob_dropout(unlabeled_data, n_drop=self.n_drop)
        log_probs = torch.log(probs)
        uncertainties = (probs*log_probs).sum(1)
        t = torch.zeros([2,n])
        t[0] = torch.from_numpy(unlabeled_idxs[uncertainties.sort()[1][:n]])
        t[1] = uncertainties.sort()[0][:n]
        return t

