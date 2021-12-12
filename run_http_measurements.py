# Original script: https://github.com/Lucapaulo/web-performance/blob/main/run_measurements.py

import re
import time
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as chromeOptions
import sys
from datetime import datetime
import hashlib
import uuid
import os
import csv

# performance elements to extract
measurement_elements = ('protocol', 'server', 'domain', 'timestamp', 'connectEnd', 'connectStart', 'domComplete',
                        'domContentLoadedEventEnd', 'domContentLoadedEventStart', 'domInteractive', 'domainLookupEnd',
                        'domainLookupStart', 'duration', 'encodedBodySize', 'decodedBodySize', 'transferSize',
                        'fetchStart', 'loadEventEnd', 'loadEventStart', 'requestStart', 'responseEnd', 'responseStart',
                        'secureConnectionStart', 'startTime', 'firstPaint', 'firstContentfulPaint', 'nextHopProtocol', 'cacheWarming', 'error')

file_elements = ('pep', 'run')

# retrieve input params
try:
    protocol = sys.argv[1]
    server = sys.argv[2]
    chrome_path = sys.argv[3]
    output_dir = sys.argv[4]
    file_elements_values = sys.argv[5].split(';')
except IndexError:
    print("Input params incomplete (protocol, server, chrome_driver, output_dir)")
    sys.exit(1)

if len(file_elements) != len(file_elements_values):
    print("Number of file elements does not match")
    sys.exit(1)

# Chrome options
chrome_options = chromeOptions()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-dev-shm-usage')
if protocol == 'quic':
    chrome_options.add_argument('--enable-quic')
    chrome_options.add_argument('--origin-to-force-quic-on=example.com:443')
chrome_options.add_argument('--allow_unknown_root_cer')
chrome_options.add_argument('--disable_certificate_verification')
chrome_options.add_argument('--ignore-urlfetcher-cert-requests')
chrome_options.add_argument(f"--host-resolver-rules=MAP example.com {server}")
chrome_options.add_argument('--verbose')
chrome_options.add_argument('--disable-http-cache')
# Function to create: openssl x509 -pubkey < "pubkey.pem" | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | base64 > "fingerprints.txt"
chrome_options.add_argument('--ignore-certificate-errors-spki-list=D29LAH0IMcLx/d7R2JAH5bw/YKYK9uNRYc6W0/GJlS8=')

def create_driver():
    return webdriver.Chrome(options=chrome_options, executable_path=chrome_path)


def get_page_performance_metrics(driver, page):
    script = """
            // Get performance and paint entries
            var perfEntries = performance.getEntriesByType("navigation");
            var paintEntries = performance.getEntriesByType("paint");
    
            var entry = perfEntries[0];
            var fpEntry = paintEntries[0];
            var fcpEntry = paintEntries[1];
    
            // Get the JSON and first paint + first contentful paint
            var resultJson = entry.toJSON();
            resultJson.firstPaint = 0;
            resultJson.firstContentfulPaint = 0;
            try {
                for (var i=0; i<paintEntries.length; i++) {
                    var pJson = paintEntries[i].toJSON();
                    if (pJson.name == 'first-paint') {
                        resultJson.firstPaint = pJson.startTime;
                    } else if (pJson.name == 'first-contentful-paint') {
                        resultJson.firstContentfulPaint = pJson.startTime;
                    }
                }
            } catch(e) {}
            
            return resultJson;
            """
    try:
        driver.set_page_load_timeout(60)
        if protocol == 'quic':
            driver.get(f'https://{page}')
        else:
            driver.get(f'http://{page}')
        return driver.execute_script(script)
    except selenium.common.exceptions.WebDriverException as e:
        return {'error': str(e)}


def perform_page_load(page, cache_warming=0):
    driver = create_driver()
    timestamp = datetime.now()
    performance_metrics = get_page_performance_metrics(driver, page)
    #driver.quit()
    # insert page into database
    if 'error' not in performance_metrics:
        # Print page source
        # print(driver.page_source)
        driver.save_screenshot(f'{output_dir}/screenshot.png')
        insert_performance(page, performance_metrics, timestamp, cache_warming=cache_warming)
    else:
        insert_performance(page, {k: 0 for k in measurement_elements}, timestamp, cache_warming=cache_warming,
                           error=performance_metrics['error'])


def create_measurements_table():
    new = False
    global local_csvfile
    file_path = f'{output_dir}/http.csv' if file_elements_values[0] == 'false' else f'{output_dir}/http_pep.csv'
    if os.path.isfile(file_path):
        local_csvfile = open(file_path, mode='a')
    else:
        local_csvfile = open(file_path, mode='w')
        new = True
    global csvfile
    csvfile = csv.writer(local_csvfile, delimiter=';')
    if new == True:
        headers = file_elements + measurement_elements
        csvfile.writerow(headers)

def insert_performance(page, performance, timestamp, cache_warming=0, error=''):
    performance['protocol'] = protocol
    performance['server'] = server
    performance['domain'] = page
    performance['timestamp'] = timestamp
    performance['cacheWarming'] = cache_warming
    performance['error'] = error
    values = file_elements_values.copy()

    for m_e in measurement_elements:
        values.append(performance[m_e])

    csvfile.writerow(values)

create_measurements_table()
# performance measurement
perform_page_load("example.com")

local_csvfile.close()
