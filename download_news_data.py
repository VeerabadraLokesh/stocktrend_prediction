import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from time import sleep
from tqdm import tqdm
from collections import defaultdict
from itertools import islice
import os
import json
from requests.adapters import HTTPAdapter, Retry

from dataset import load_dataset,get_path

dataset_name ='miguelaenlle/massive-stock-news-analysis-db-for-nlpbacktests'
file_name = 'raw_analyst_ratings.csv'

raw_data_dir = os.path.join(get_path(dataset_name), 'raw_data')
os.makedirs(raw_data_dir, exist_ok=True)



out_file = os.path.join(raw_data_dir, f"data.csv")
lock_file = os.path.join(raw_data_dir, f"run.lock")
track_file = os.path.join(raw_data_dir, "track.num")
if os.path.isfile(lock_file):
    print("Lock file found exiting")
    exit(0)

with open(lock_file, "w") as wf:
    wf.write("locked")

raw_analyst_ratings_df = load_dataset(dataset_name, file_name)
# raw_analyst_ratings_df = pd.read_csv('raw_analyst_ratings.csv')
num_rows = len(raw_analyst_ratings_df)
start = num_rows//2
end = num_rows

if os.path.isfile(track_file):
    with open(track_file, 'r') as tf:
        try:
            x = int(tf.read())
            if x > start and x <= end:
                start = x
        except:
            pass

print(start, end)

retries = 3
backoff = 0.5
backoff_factor = [backoff * (2 ** i) for i in range(retries)]

news_body = {}

try:
    for _idx, row in tqdm(islice(raw_analyst_ratings_df.iterrows(), start, end)):
        
        url = row['url']
        date = row['date']
        idx = row['Unnamed: 0']
        
        html_content = None

        for r in range(retries):
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    html_content = response.text
                    break
                elif response.status_code == 429:
                    sleep(5)
                else:
                    print(f"Failed with {response.status_code} while retrieving: {url}")
                    sleep(backoff_factor[r])
            except KeyboardInterrupt as kbe:
                raise kbe
            except Exception as e:
                print(e)

        soup = BeautifulSoup(html_content, 'html.parser')
        raw_main_content = str(soup.find("div", {"class": "main-content-container"})).replace("\n", "").replace("\t", "")
        news_body[idx] = raw_main_content
        if _idx % 100 == 99:
            with open(out_file, 'a') as wf:
                for k, v in news_body.items():
                    wf.write(f"{k}\t{v}\n")
                news_body.clear()
            with open(track_file, 'w') as wtf:
                wtf.write(f"{(_idx+start)}")
        time.sleep(0.3)

except KeyboardInterrupt:
    print("Keyboard interrupt, exiting safely")
except Exception as e:
    print(e)
finally:
    with open(out_file, 'a') as wf:
        for k, v in news_body.items():
            wf.write(f"{k}\t{v}\n")
        news_body.clear()
    os.remove(lock_file)
    with open(track_file, 'w') as wtf:
        wtf.write(f"{(_idx+start)}")
