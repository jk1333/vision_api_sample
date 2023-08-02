from joblib import Parallel, delayed
from google.cloud import storage
import urllib
from os.path import basename
import pandas as pd
import sys
import itertools
from google.cloud import vision
FILENAME = sys.argv[1]
PROJECT_ID = sys.argv[2]
BUCKET = sys.argv[3]
LOCATION = "us-west1"

#Process sources
def applyRule(image_uris):
    errors = []
    bucket = storage.Client().get_bucket(BUCKET)
    try:
        for image_uri in image_uris:
            with urllib.request.urlopen(image_uri) as response:
                bucket.blob(f"images/{basename(response.url)}").upload_from_string(response.read())
    except:
        errors.append(image_uri)
    return errors

product_df = pd.read_csv(f"https://raw.githubusercontent.com/williamtsoi1/vision-api-product-search-demo/main/data/{FILENAME}")
nitems = 20
data = product_df['image-uri'].to_list()
chunks = [data[x:x+nitems] for x in range(0, len(data), nitems)]
result = Parallel(n_jobs=10, verbose=10)(delayed(applyRule)(image_uris) for image_uris in chunks)
result = list(itertools.chain.from_iterable(result))
product_df = product_df[~product_df['image-uri'].isin(result)]
product_df["image-uri"] = product_df["image-uri"].apply(basename)
product_df["image-uri"] = f"gs://{BUCKET}/images/" + product_df["image-uri"]
product_df.to_csv(f"gs://{BUCKET}/result/{FILENAME}", index=False)

def import_product_sets(project_id, location, gcs_uri):
    """Import images of different products in the product set.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        gcs_uri: Google Cloud Storage URI.
            Target files must be in Product Search CSV format.
    """
    client = vision.ProductSearchClient()

    # A resource that represents Google Cloud Platform location.
    location_path = f"projects/{project_id}/locations/{location}"

    # Set the input configuration along with Google Cloud Storage URI
    gcs_source = vision.ImportProductSetsGcsSource(csv_file_uri=gcs_uri)
    input_config = vision.ImportProductSetsInputConfig(gcs_source=gcs_source)

    # Import the product sets from the input URI.
    response = client.import_product_sets(
        parent=location_path, input_config=input_config
    )

    print(f"Processing operation name: {response.operation.name}")
    # synchronous check of operation status
    result = response.result()
    print("Processing done.")

    for i, status in enumerate(result.statuses):
        print("Status of processing line {} of the csv: {}".format(i, status))
        # Check the status of reference image
        # `0` is the code for OK in google.rpc.Code.
        if status.code == 0:
            reference_image = result.reference_images[i]
            print(reference_image)
        else:
            print(f"Status code not OK: {status.message}")

import_product_sets(PROJECT_ID, LOCATION, f"gs://{BUCKET}/result/{FILENAME}")