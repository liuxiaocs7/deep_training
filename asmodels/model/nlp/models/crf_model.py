# -*- coding: utf-8 -*-
# @Time    : 2022/11/15 12:26
import torch
from torch import nn
from transformers import AdamW, get_linear_schedule_with_warmup
from .transformer import TransformerModel
from ..layers.crf import CRF
from ..utils import configure_optimizers
__all__ = [
    'TransformerForCRF'
]

class TransformerForCRF(TransformerModel):
    def __init__(self,config, train_args,with_efficient=True, *args,**kwargs):
        super(TransformerForCRF, self).__init__(config, train_args,*args,**kwargs)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, config.num_labels)
        self.crf = CRF(num_tags=config.num_labels)

    def configure_optimizers(self):
        attrs = [(self.model,self.config.task_specific_params['learning_rate']),
                 (self.classifier,self.config.task_specific_params['learning_rate_for_task']),
                 (self.crf, self.config.task_specific_params['learning_rate_for_task']),
                 ]
        return configure_optimizers(attrs, self.hparams,self.trainer.estimated_stepping_batches)

    def training_step(self, batch, batch_idx):
        labels: torch.Tensor = batch.pop('labels')
        attention_mask = batch['attention_mask']
        outputs = self(**batch)
        logits = outputs[0]
        logits = self.classifier(logits)

        loss = None
        if labels is not None:
            labels = torch.where(labels >= 0, labels, torch.zeros_like(labels))
            loss = self.crf(emissions=logits, tags=labels, mask=attention_mask)
            # outputs = (-1 * loss,) + outputs
        # else:
        #     # tags = self.crf.decode(logits, attention_mask)
        #     # outputs = (tags,)

        self.log_dict({'train_loss': loss}, prog_bar=True)
        return loss