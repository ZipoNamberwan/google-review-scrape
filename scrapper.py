import argparse
from googlemapsscrapper import GoogleMapsScraper
from termcolor import colored
import random
import time
import csv
import os
import json

HEADER = ['name', 'username', 'user_photo',
          'rating', 'timestamp', 'caption', 'review_id', 'waktu_kunjungan', 'waktu_antrean', 'reservasi']

def load_active_place(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        places = json.load(f)
    for place in places:
        if place.get('active'):
            return place
    raise Exception("No active place found in JSON.")

def csv_writer(outpath):
    csv_path = 'data/' + outpath
    file_exists = os.path.exists(csv_path)
    last_row = 0
    targetfile = open(csv_path, mode='a' if file_exists else 'w', encoding='utf-8', newline='\n')
    # Use quoting=csv.QUOTE_ALL to ensure all fields (including name) are quoted
    writer = csv.writer(targetfile, quoting=csv.QUOTE_ALL)
    if not file_exists:
        writer.writerow(HEADER)
    else:
        with open(csv_path, encoding='utf-8') as f:
            next(f, None)
            last_row = sum(1 for _ in f)
    return writer, last_row, targetfile

def get_last_row_count(csv_path):
    path = 'data/' + csv_path
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        # Skip the header row
        next(f, None)
        row_count = sum(1 for _ in f)
    return row_count

def stats_writer():
    stats_path = 'data/stats.csv'
    stats_exists = os.path.exists(stats_path)
    stats_file = open(stats_path, mode='a', encoding='utf-8', newline='\n')
    writer = csv.writer(stats_file)
    if not stats_exists:
        writer.writerow(['place', 'batch_start', 'batch_end', 'batch_size', 'seconds'])
    return writer, stats_file

def load_places_to_execute(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        places = json.load(f)
    # Filter by execute==true, sort by order
    return sorted(
        [p for p in places if p.get('execute', False)],
        key=lambda x: x.get('order', 0)
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='places.json', help='Path to places config JSON')
    parser.add_argument('--source', dest='source', action='store_true',
                        help='Add source url to CSV file (for multiple urls in a single file)')
    args = parser.parse_args()

    places = load_places_to_execute(args.config)
    stats_writer_obj, stats_file = stats_writer()

    for place in places:
        url = place['url']
        loadmore_fullxpath = place['loadmore_fullxpath']
        newest_fullxpath = place['newest_fullxpath']
        name = place['name']
        review_limit = place.get('review_limit', 0)

        writer, last_row, targetfile = csv_writer(f"{name}.csv")
        print(colored(f"Resuming {name} from review {last_row}", "yellow"))

        # Always create a new scraper instance for each place to ensure a fresh driver
        scraper = GoogleMapsScraper(
            loadmore_fullxpath=loadmore_fullxpath,
            newest_fullxpath=newest_fullxpath
        )
        BATCH_SIZE = 1000
        error = scraper.start(url)
        if error == 0:
            n = last_row
            if n > 0:
                print(colored(f"Loading reviews until {n} items are shown...", "yellow"))
                scraper.load_until_count(n)
                print(colored(f"Loaded {n} reviews. Starting to save new reviews...", "green"))
            while n < review_limit:
                try:
                    target = min(n + BATCH_SIZE, review_limit)
                    print(colored(f"Loading reviews until {target} items are shown...", "yellow"))
                    batch_start_time = time.time()
                    scraper.load_until_count(target)
                    print(colored(f"Loaded {target} reviews. Expanding and parsing batch...", "green"))
                    reviews = scraper.expand_and_parse_batch(n, target)
                    if len(reviews) == 0:
                        break
                    for r in reviews:
                        row_data = list(r.values())
                        if args.source:
                            row_data.append(url[:-1])
                        writer.writerow(row_data)
                    batch_elapsed = time.time() - batch_start_time
                    # Add place name to stats
                    stats_writer_obj.writerow([name, n, n + len(reviews) - 1, len(reviews), f"{batch_elapsed:.2f}"])
                    stats_file.flush()
                    n += len(reviews)
                    delay = random.uniform(0, 2)
                    print(colored(f"Sleeping for {delay:.2f} seconds...", "yellow"))
                    time.sleep(delay)
                except Exception as e:
                    print(colored(f"Error at review {n}: {e}", "red"))
                    n += 1
                    continue
        
        print(colored(f"Finishing {name}", "red"))
        time.sleep(10)
        
if __name__ == "__main__":
    main()
