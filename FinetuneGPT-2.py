# -*- coding: utf-8 -*-
"""HW3.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11UysXKmotwFCPYqQHY2pa24K1zmHAICR
"""

#SOURCE CODE: https://colab.research.google.com/drive/13dZVYEOMhXhkXWfvSMVM1TTtUDrT6Aeh?usp=sharing#scrollTo=JCCeyhuDHdOu 

#As is
pip install transformers

#Removed libraries from the other code that were irrelevant such as seaborn and matplotlib.pyplot.
import os
import time
import datetime
import pandas as pd
import numpy as np
import random
#imported the math library as it is needed for ca;culating perplexity.
import math

import torch
from torch.utils.data import Dataset, DataLoader, random_split, RandomSampler, SequentialSampler
torch.manual_seed(42)

from transformers import GPT2LMHeadModel,  GPT2Tokenizer, GPT2Config, GPT2LMHeadModel
from transformers import AdamW, get_linear_schedule_with_warmup

import nltk
nltk.download('punkt')

!nvidia-smi

#Added this code to read the text file and remove any lines that do not contain any characters.
file1 = open("HGWells.txt","r+")
x = file1.readlines()
count = 0
for text in x:  
  if(len(text) == 1 ):
    del x[count]
  count+=1
print(x)

#As is. This block of code is for calculating the number of tokens.
doc_lengths = []
for textline in x:
    # Using the nltk tokenizer to get a rough token count distribution
    tokens = nltk.word_tokenize(textline)
    print(tokens)
    doc_lengths.append(len(tokens))
doc_lengths = np.array(doc_lengths)

#This code has been added to count the total number of tokens in the corpus, as well as the number of tokens in each novel that was included in this corpus.
count = 0 
i = 0
j = 0
count_temp = 0
for y in doc_lengths:
  count = count+y
  count_temp = count_temp+y
  if(j == 19):
    print(count_temp)
    j=0
    count_temp = 0
  else:
    j+=1
  i+=1
  
print(count)
print(i)

# Load the GPT tokenizer.
#As is.
tokenizer = GPT2Tokenizer.from_pretrained('gpt2', bos_token='<|startoftext|>', eos_token='<|endoftext|>', pad_token='<|pad|>')

#As is.
batch_size = 2

#As is.
class GPT2Dataset(Dataset):

  def __init__(self, txt_list, tokenizer, gpt2_type="gpt2", max_length=1024):

    self.tokenizer = tokenizer
    self.input_ids = []
    self.attn_masks = []

    for txt in txt_list:

      encodings_dict = tokenizer('<|startoftext|>'+ txt + '<|endoftext|>', truncation=True, max_length=max_length, padding="max_length")

      self.input_ids.append(torch.tensor(encodings_dict['input_ids']))
      self.attn_masks.append(torch.tensor(encodings_dict['attention_mask']))
    
  def __len__(self):
    return len(self.input_ids)

  def __getitem__(self, idx):
    return self.input_ids[idx], self.attn_masks[idx]

#In this piece of code I have changed the max_length to 1024.
dataset = GPT2Dataset(x, tokenizer, max_length=1024)
# Split into training and validation sets
train_size = int(0.9 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

print('{:>5,} training samples'.format(train_size))
print('{:>5,} validation samples'.format(val_size))

#As is.
train_dataloader = DataLoader(
            train_dataset,  
            sampler = RandomSampler(train_dataset), 
            batch_size = batch_size
        )


validation_dataloader = DataLoader(
            val_dataset, 
            sampler = SequentialSampler(val_dataset), 
            batch_size = batch_size 
        )

#As is.
configuration = GPT2Config.from_pretrained('gpt2', output_hidden_states=False)
# instantiate the model
model = GPT2LMHeadModel.from_pretrained("gpt2", config=configuration)

model.resize_token_embeddings(len(tokenizer))

device = torch.device("cuda")
model.cuda()
seed_val = 42

random.seed(seed_val)
np.random.seed(seed_val)
torch.manual_seed(seed_val)
torch.cuda.manual_seed_all(seed_val)

#Changed the number of epochs to 10.
epochs = 10
learning_rate = 5e-4
warmup_steps = 1e2
epsilon = 1e-8
# this produces sample output every 100 steps
sample_every = 100

#As is.
optimizer = AdamW(model.parameters(),
                  lr = learning_rate,
                  eps = epsilon
                )

#As is.
# Total number of training steps is [number of batches] x [number of epochs]. 
# (Note that this is not the same as the number of training samples).
total_steps = len(train_dataloader) * epochs

# Create the learning rate scheduler.
# This changes the learning rate as the training loop progresses
scheduler = get_linear_schedule_with_warmup(optimizer, 
                                            num_warmup_steps = warmup_steps, 
                                            num_training_steps = total_steps)

#As is
def format_time(elapsed):
    return str(datetime.timedelta(seconds=int(round((elapsed)))))

#Added this code to login to HuggingFace.
from huggingface_hub import notebook_login

notebook_login()

#Added this code to import the math library.
import math

#I modified this code to calculate training and validation perplexity.
total_t0 = time.time()

training_stats = []

model = model.to(device)

for epoch_i in range(0, epochs):

    # ========================================
    #               Training
    # ========================================

    print("")
    print('======== Epoch {:} / {:} ========'.format(epoch_i + 1, epochs))
    print('Training...')

    t0 = time.time()

    total_train_loss = 0

    model.train()

    for step, batch in enumerate(train_dataloader):

        b_input_ids = batch[0].to(device)
        b_labels = batch[0].to(device)
        b_masks = batch[1].to(device)

        model.zero_grad()        

        outputs = model(  b_input_ids,
                          labels=b_labels, 
                          attention_mask = b_masks,
                          token_type_ids=None
                        )

        loss = outputs[0]  

        batch_loss = loss.item()
        total_train_loss += batch_loss

        # Get sample every x batches.
        if step % sample_every == 0 and not step == 0:

            elapsed = format_time(time.time() - t0)
            print('  Batch {:>5,}  of  {:>5,}. Loss: {:>5,}.   Elapsed: {:}.'.format(step, len(train_dataloader), batch_loss, elapsed))

            model.eval()
            
            sample_outputs = model.generate(
                                    bos_token_id=random.randint(1,30000),
                                    do_sample=True,   
                                    top_k=50, 
                                    max_length = 300,
                                    top_p=0.95, 
                                    num_return_sequences=1
                                )
            for i, sample_output in enumerate(sample_outputs):
                  print("{}: {}".format(i, tokenizer.decode(sample_output, skip_special_tokens=True)))
            
            model.train()

        loss.backward()

        optimizer.step()

        scheduler.step()

    # Calculate the average loss over all of the batches.
    avg_train_loss = total_train_loss / len(train_dataloader)       
    
    # Measure how long this epoch took.
    training_time = format_time(time.time() - t0)

    print("")
    print("  Average training loss: {0:.2f}".format(avg_train_loss))
    #Added this code to calculate training perplexity.
    avg_train_perplexity = math.exp(avg_train_loss)
    print("  Average training perplexity: {0:.2f}".format(avg_train_perplexity))
    print("  Training epoch took: {:}".format(training_time))
        
    # ========================================
    #               Validation
    # ========================================

    print("")
    print("Running Validation...")

    t0 = time.time()

    model.eval()

    total_eval_loss = 0
    nb_eval_steps = 0

    # Evaluate data for one epoch
    for batch in validation_dataloader:
        
        b_input_ids = batch[0].to(device)
        b_labels = batch[0].to(device)
        b_masks = batch[1].to(device)
        
        with torch.no_grad():        

            outputs  = model(b_input_ids, 
#                            token_type_ids=None, 
                             attention_mask = b_masks,
                            labels=b_labels)
          
            loss = outputs[0]  
            
        batch_loss = loss.item()
        total_eval_loss += batch_loss        

    avg_val_loss = total_eval_loss / len(validation_dataloader)
    
    validation_time = format_time(time.time() - t0)    

    print("  Validation Loss: {0:.2f}".format(avg_val_loss))
    #Added this code to calculate validation perplexity.
    avg_validation_perplexity = math.exp(avg_val_loss)
    print("  Average validation perplexity: {0:.2f}".format(avg_validation_perplexity))
    print("  Validation took: {:}".format(validation_time))

    # Record all statistics from this epoch.
    training_stats.append(
        {
            'epoch': epoch_i + 1,
            'Training Loss': avg_train_loss,
            'Valid. Loss': avg_val_loss,
            'Training Time': training_time,
            'Validation Time': validation_time
        }
    )

print("")
print("Training complete!")
print("Total training took {:} (h:mm:ss)".format(format_time(time.time()-total_t0)))
model.push_to_hub("MinzaKhan/HGWells")
tokenizer.push_to_hub("MinzaKhan/HGWells")

model.eval()
#I modified this piece of code to change the starting promt to "I".
prompt = "<|startoftext|> I"

generated = torch.tensor(tokenizer.encode(prompt)).unsqueeze(0)
generated = generated.to(device)

sample_outputs = model.generate(
                                generated,
                                do_sample=True,   
                                top_k=50, 
                                max_length = 200,
                                top_p=0.95, 
                                num_return_sequences=1
                                )

for i, sample_output in enumerate(sample_outputs):
  print("1: {}\n\n".format(tokenizer.decode(sample_output, skip_special_tokens=True)))

#I added this code and set the starting prompt to "Who"
prompt = "<|startoftext|> Who"

generated = torch.tensor(tokenizer.encode(prompt)).unsqueeze(0)
generated = generated.to(device)

sample_outputs = model.generate(
                                generated,
                                do_sample=True,   
                                top_k=50, 
                                max_length = 200,
                                top_p=0.95, 
                                num_return_sequences=1
                                )

for i, sample_output in enumerate(sample_outputs):
  print("1: {}\n\n".format(tokenizer.decode(sample_output, skip_special_tokens=True)))

#I added this code and set the starting prompt to "When"
prompt = "<|startoftext|> When"

generated = torch.tensor(tokenizer.encode(prompt)).unsqueeze(0)
generated = generated.to(device)

sample_outputs = model.generate(
                                generated,
                                do_sample=True,   
                                top_k=50, 
                                max_length = 200,
                                top_p=0.95, 
                                num_return_sequences=1
                                )

for i, sample_output in enumerate(sample_outputs):
  print("1: {}\n\n".format(tokenizer.decode(sample_output, skip_special_tokens=True)))