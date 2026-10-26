import os
import json
import time
import logging
from datetime import datetime, timezone

import requests
from botocore.exceptions import ClientError
import boto3

STORE_DOMAIN= "gymshark.com"
BUCKET_NAME = "gymshark-data-lake-sumit-07"
AWS_REGION = "ap-southeast-2"

RUN_DATE= datetime.now(timezone.utc).strftime("%Y-%m-%d")
S3_PREFIX= f"raw/shopify/dt={RUN_DATE}"
#-logging-
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

#---intialize s3 client-
try:
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    logger.info("S3 client initialized successfully.")
except Exception as e: 
    logger.error(f"Failed to initialize S3 client: {e}")
    raise 

#-the scraper function-
def fetch_page(domain:str, page_number:int) -> list:
    url=f"https://{domain}/products.json?limit=250&page={page_number}"

    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"

    }

    try:
        response=requests.get(url,headers=headers,timeout=15)

        if response.status_code==200:
            data=response.json()
            return data.get("products", [])
        elif response.status_code ==429:
            logger.warning(f"Rate limited on page {page_number}. Retrying after 25  seconds...")
            time.sleep(25)
            return fetch_page(domain, page_number)
        elif response.status_code == 403:
            logger.error(f"Access forbidde  on page {page_number}. the store blocking the request")
            return []

        else:
            logger.error(f"Unexpected status {response.status_code} on page {page_number}. Retrying after 10 seconds...")
            return []

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for page {page_number}: {e}")
        return []


# main pipeline function

def run_ingestion():
    page=1
    total_products=0

    while True:
        logger.info(f"Processing page {page}...")

        products=fetch_page(STORE_DOMAIN, page)

        if not products:
            logger.info("Received an empty page. Pagination complete.")
            break
        if page>50:
            logger.warning("Reached Shopify's 50-page pagination limit. Stopping further requests.")
            break
        s3_key = f"{S3_PREFIX}/page_{page:03d}.json"
        json_payload = json.dumps(products, ensure_ascii=False)
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=json_payload.encode("utf-8"),
                ContentType="application/json"
            )
            logger.info(f"Uploaded {len(products)} products to s3://{BUCKET_NAME}/{s3_key}")
            
            total_products += len(products)

        except ClientError as e:
            logger.error(f"Failed to upload page {page} to S3: {e}")
            break

        if len(products) < 250:
            logger.info(f"Page {page} returned {len(products)} products (<250). Reached the end.")
            break

        page += 1

        time.sleep(1)  # Sleep for 1 second between requests to avoid rate limiting

    logger.info(f"Ingestion complete. Total products scraped: {total_products}")

# execution guard

if __name__ == "__main__":
    logger.info(f"Starting ingestion for {STORE_DOMAIN} into bucket '{BUCKET_NAME}'....")
    run_ingestion()



