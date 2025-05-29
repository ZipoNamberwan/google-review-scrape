import argparse
from googlemapsscrapper import GoogleMapsScraper
from termcolor import colored
import random
import time
import csv

# HEADER = ['id_review', 'caption', 'relative_date', 'retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user']
HEADER = ['name', 'username', 'user_photo',
          'rating', 'timestamp', 'caption', 'review_id', 'waktu_kunjungan', 'waktu_antrean', 'reservasi']

def csv_writer(outpath):
    targetfile = open('data/' + outpath, mode='w',
                      encoding='utf-8', newline='\n')
    writer = csv.writer(targetfile, quoting=csv.QUOTE_MINIMAL)
    h = HEADER
    writer.writerow(h)

    return writer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-N', type=int, default=1, help='Number of iterations')
    parser.add_argument('--o', type=str, default='output.csv',
                        help='output directory')
    parser.add_argument('--source', dest='source', action='store_true',
                        help='Add source url to CSV file (for multiple urls in a single file)')

    args = parser.parse_args()

    writer = csv_writer(args.o)

    # Read URLs from urls.txt
    with open('urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    scraper = GoogleMapsScraper()
    for url in urls:
        # Await the coroutine if start is async
        error = scraper.start(url)
        if error == 0:
            n = 0
            while n < args.N:
                # logging to std out
                print(colored('[Review ' + str(n) + ']', 'cyan'))
                reviews = scraper.get_reviews(n)
                if len(reviews) == 0:
                    break
                for r in reviews:
                    row_data = list(r.values())
                    if args.source:
                        row_data.append(url[:-1])

                    writer.writerow(row_data)

                n += len(reviews)
                # Add random delay to mimic human behavior
                delay = random.uniform(2, 4)
                print(
                    colored(f"Sleeping for {delay:.2f} seconds...", "yellow"))
                time.sleep(delay)


if __name__ == "__main__":
    main()
