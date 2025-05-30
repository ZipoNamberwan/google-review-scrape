import argparse
from googlemapsscrapper import GoogleMapsScraper
from termcolor import colored
import random
import time
import csv
import os

# HEADER = ['id_review', 'caption', 'relative_date', 'retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user']
HEADER = ['name', 'username', 'user_photo',
          'rating', 'timestamp', 'caption', 'review_id', 'waktu_kunjungan', 'waktu_antrean', 'reservasi']

def csv_writer(outpath):
    csv_path = 'data/' + outpath
    file_exists = os.path.exists(csv_path)
    last_row = 0
    targetfile = open(csv_path, mode='a' if file_exists else 'w', encoding='utf-8', newline='\n')
    writer = csv.writer(targetfile, quoting=csv.QUOTE_MINIMAL)
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-N', type=int, default=1, help='Number of iterations')
    parser.add_argument('--o', type=str, default='output.csv',
                        help='output directory')
    parser.add_argument('--source', dest='source', action='store_true',
                        help='Add source url to CSV file (for multiple urls in a single file)')

    args = parser.parse_args()

    writer, last_row, targetfile = csv_writer(args.o)
    print(colored(f"Resuming from review {last_row}", "yellow"))

    # Read URLs from urls.txt
    with open('urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    scraper = GoogleMapsScraper()
    BATCH_SIZE = 1000
    for url in urls:
        error = scraper.start(url)
        if error == 0:
            n = last_row
            if n > 0:
                print(colored(f"Loading reviews until {n} items are shown...", "yellow"))
                scraper.load_until_count(n)
                print(colored(f"Loaded {n} reviews. Starting to save new reviews...", "green"))
            while n < args.N:
                try:
                    target = min(n + BATCH_SIZE, args.N)
                    print(colored(f"Loading reviews until {target} items are shown...", "yellow"))
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
                    targetfile.flush()  # <-- flush after each batch
                    n += len(reviews)
                    delay = random.uniform(0, 2)
                    print(colored(f"Sleeping for {delay:.2f} seconds...", "yellow"))
                    time.sleep(delay)
                except Exception as e:
                    print(colored(f"Error at review {n}: {e}", "red"))
                    n += 1
                    continue


if __name__ == "__main__":
    main()
