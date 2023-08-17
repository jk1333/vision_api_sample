from google.cloud import vision
import streamlit as st
import pandas as pd
import sys
PROJECT_ID = sys.argv[1]

st.set_page_config(page_title='Vision AI product search test', 
                    page_icon=None, 
                    layout="wide", 
                    initial_sidebar_state="auto", 
                    menu_items=None)

@st.cache_resource
def prepare_imagelist():
    li = []
    for filename in ["products_0.csv", "products_1.csv", "products_2.csv"]:
        df = pd.read_csv(f"https://raw.githubusercontent.com/williamtsoi1/vision-api-product-search-demo/main/data/{filename}", index_col=None)
        li.append(df)
    return pd.concat(li, axis=0, ignore_index=True)[['product-id', 'image-uri']]

@st.cache_resource
def prepare_client():
    return vision.ProductSearchClient(), vision.ImageAnnotatorClient()

product_search_client, image_annotator_client = prepare_client()
images_df = prepare_imagelist()

def get_similar_products_file(project_id, location, product_set_id, 
                              product_category, content, filter, max_results):
    image = vision.Image(content=content)

    # product search specific parameters
    product_set_path = product_search_client.product_set_path(
        project=project_id, location=location, product_set=product_set_id
    )
    product_search_params = vision.ProductSearchParams(
        product_set=product_set_path,
        product_categories=[product_category],
        filter=filter,
    )
    image_context = vision.ImageContext(product_search_params=product_search_params)

    # Search products similar to the image.
    response = image_annotator_client.product_search(
        image, image_context=image_context, max_results=max_results
    )

    index_time = response.product_search_results.index_time
    st.write(f"Product set index time: {index_time}")

    return response.product_search_results.results

results = []
uploaded_file = st.file_uploader("Choose a image", ['png', 'jpg'])
if uploaded_file is not None:
    # To read file as bytes:
    bytes_data = uploaded_file.getvalue()
    st.image(bytes_data, "Source", 400)
    with st.spinner('Analyzing...'):
        results = get_similar_products_file(PROJECT_ID, "us-west1", "products", "general-v1", 
                                            bytes_data, None, 4)
if len(results) > 0:
    cols = st.columns(len(results))
    for idx, result in enumerate(results):
        product = result.product
        title = f"{product.display_name}, Score: {result.score:.2f}"
        id = product.name[product.name.rfind('/')+1:]
        cols[idx].image(images_df[images_df['product-id'] == int(id)]['image-uri'].values[0], title, 200)