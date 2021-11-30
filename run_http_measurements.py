# Original script: https://github.com/Lucapaulo/web-performance/blob/main/run_measurements.py

import re
import time
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as chromeOptions
import sys
import sqlite3
from datetime import datetime
import hashlib
import uuid
import os

# performance elements to extract
measurement_elements = ('id', 'protocol', 'server', 'domain', 'timestamp', 'connectEnd', 'connectStart', 'domComplete',
                        'domContentLoadedEventEnd', 'domContentLoadedEventStart', 'domInteractive', 'domainLookupEnd',
                        'domainLookupStart', 'duration', 'encodedBodySize', 'decodedBodySize', 'transferSize',
                        'fetchStart', 'loadEventEnd', 'loadEventStart', 'requestStart', 'responseEnd', 'responseStart',
                        'secureConnectionStart', 'startTime', 'nextHopProtocol', 'cacheWarming', 'error')

# create db
db = sqlite3.connect('web-performance.db')
cursor = db.cursor()

# retrieve input params
try:
    protocol = sys.argv[1]
    server = sys.argv[2]
    chrome_path = sys.argv[3]
except IndexError:
    print("Input params incomplete (protocol, server, chrome_driver)")
    sys.exit(1)

# Chrome options
chrome_options = chromeOptions()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--enable-quic')
chrome_options.add_argument('--origin-to-force-quic-on=example.com:443')
chrome_options.add_argument('--allow_unknown_root_cer')
chrome_options.add_argument('--disable_certificate_verification')
chrome_options.add_argument('--ignore-urlfetcher-cert-requests')
chrome_options.add_argument(f'--host-resolver-rules="MAP example.com {server}"')


def create_driver():
    return webdriver.Chrome(options=chrome_options, executable_path=chrome_path)


def get_page_performance_metrics(driver, page):
    script = """
            // Get a resource performance entry
            var perfEntries = performance.getEntriesByType("navigation");

            var entry = perfEntries[0];

            // Get the JSON
            return entry.toJSON();
            """
    try:
        driver.set_page_load_timeout(30)
        driver.get(f'https://{page}')
        return driver.execute_script(script)
    except selenium.common.exceptions.WebDriverException as e:
        return {'error': str(e)}


def perform_page_load(page, cache_warming=0):
    driver = create_driver()
    timestamp = datetime.now()
    performance_metrics = get_page_performance_metrics(driver, page)
    driver.quit()
    # insert page into database
    if 'error' not in performance_metrics:
        insert_performance(page, performance_metrics, timestamp, cache_warming=cache_warming)
    else:
        insert_performance(page, {k: 0 for k in measurement_elements}, timestamp, cache_warming=cache_warming,
                           error=performance_metrics['error'])


def create_measurements_table():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id string,
            protocol string,
            server string,
            domain string,
            timestamp datetime,
            connectEnd integer,
            connectStart integer,
            domComplete integer,
            domContentLoadedEventEnd integer,
            domContentLoadedEventStart integer,
            domInteractive integer,
            domainLookupEnd integer,
            domainLookupStart integer,
            duration integer,
            encodedBodySize integer,
            decodedBodySize integer,
            transferSize integer,
            fetchStart integer,
            loadEventEnd integer,
            loadEventStart integer,
            requestStart integer,
            responseEnd integer,
            responseStart integer,
            secureConnectionStart integer,
            startTime integer,
            nextHopProtocol string,
            cacheWarming integer,
            error string,
            PRIMARY KEY (id)
        );
        """)
    db.commit()


def create_qlogs_table():
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS qlogs (
                measurement_id string,
                qlog string,
                FOREIGN KEY (measurement_id) REFERENCES measurements(id)
            );
            """)
    db.commit()


def insert_performance(page, performance, timestamp, cache_warming=0, error=''):
    performance['protocol'] = protocol
    performance['server'] = server
    performance['domain'] = page
    performance['timestamp'] = timestamp
    performance['cacheWarming'] = cache_warming
    performance['error'] = error
    # generate unique ID
    sha = hashlib.md5()
    sha_input = ('' + protocol + server + page + str(cache_warming))
    sha.update(sha_input.encode())
    uid = uuid.UUID(sha.hexdigest())
    performance['id'] = str(uid)

    # insert into database
    cursor.execute(f"""
    INSERT INTO measurements VALUES ({(len(measurement_elements) - 1) * '?,'}?);
    """, tuple([performance[m_e] for m_e in measurement_elements]))
    db.commit()

    if protocol == 'quic':
        insert_qlogs(str(uid))


def insert_qlogs(uid):
    with open(f"{dnsproxy_dir}qlogs.txt", "r") as qlogs:
        log = qlogs.read()
        cursor.execute("""
            INSERT INTO qlogs VALUES (?,?);
            """, (uid, log))
        db.commit()
    # remove the qlogs after dumping it into the db
    with open(f"{dnsproxy_dir}qlogs.txt", "w") as qlogs:
        qlogs.write('')

create_measurements_table()
create_qlogs_table()
# performance measurement
perform_page_load("example.com")

db.close()
