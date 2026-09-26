import os
from azure.cosmos import CosmosClient


# configuration ---------------------------------------------

COSMOS_CONNECTION_STRING = os.getenv(
    "COSMOS_CONNECTION_STRING", " "
)

DATABASE_ID = "beautyclinicDB"
CONTAINER_ID = "BeautyClinic"

client = None
database = None
container = None


# connection ---------------------------------------------

def connect_cosmos():
    global client, database, container

    if not COSMOS_CONNECTION_STRING:
        raise ValueError(
            "COSMOS_CONNECTION_STRING is not set"
        )

    client = CosmosClient.from_connection_string(
        COSMOS_CONNECTION_STRING
    )

    database = client.get_database_client(
        DATABASE_ID
    )

    container = database.get_container_client(
        CONTAINER_ID
    )

    return container


# connection guard ---------------------------------------------

def _require_container():
    if container is None:
        raise RuntimeError(
            "cosmos db is not connected"
        )


# add product ---------------------------------------------

def add_product(
    barcode,
    brand,
    name,
    category,
    batch_code,
    expiry_date,
    initial_weight,
    current_weight=None,
    status="new",
    product_type="normal",
    last_used_date=None,
    replacement_created=0,
    replacement_source_id=None
):
    _require_container()

    barcode = str(barcode).strip()
    batch_code = str(batch_code).strip()

    if current_weight is None:
        current_weight = initial_weight

    product = {
        "id": f"{barcode}_{batch_code}",
        "barcode": barcode,
        "brand": str(brand).strip(),
        "name": str(name).strip(),
        "category": str(category).strip(),
        "batch_code": batch_code,
        "expiry_date": str(expiry_date).strip(),
        "initial_weight": float(initial_weight),
        "current_weight": float(current_weight),
        "status": str(status).lower(),
        "replacement_created": int(replacement_created),
        "replacement_source_id": replacement_source_id,
        "product_type": product_type,
        "last_used_date": last_used_date
    }

    container.create_item(
        body=product
    )

    return product


# get all products ---------------------------------------------

def get_products():
    _require_container()

    return list(
        container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True
        )
    )


# get one product ---------------------------------------------

def get_product(product_id):
    _require_container()

    query = (
        "SELECT * FROM c "
        "WHERE c.id = @id"
    )

    items = list(
        container.query_items(
            query=query,
            parameters=[
                {
                    "name": "@id",
                    "value": product_id
                }
            ],
            enable_cross_partition_query=True
        )
    )

    if not items:
        return None

    return items[0]


# update product ---------------------------------------------

def update_product(product_id, **updates):
    _require_container()

    product = get_product(product_id)

    if product is None:
        return None

    for key, value in updates.items():
        if key in (
            "initial_weight",
            "current_weight"
        ) and value is not None:
            value = float(value)

        elif key == "replacement_created" and value is not None:
            value = int(value)

        product[key] = value

    container.upsert_item(
        body=product
    )

    return product


# update current weight ---------------------------------------------

def update_product_weight(product_id, current_weight):
    return update_product(
        product_id,
        current_weight=float(current_weight)
    )


# update status ---------------------------------------------

def update_product_status(product_id, status):
    return update_product(
        product_id,
        status=str(status).lower()
    )


# update replacement flag ---------------------------------------------

def mark_replacement_created(product_id):
    return update_product(
        product_id,
        replacement_created=1
    )


# replacement lookup ---------------------------------------------

def replacement_exists_for(source_product_id):
    _require_container()

    query = (
        "SELECT VALUE COUNT(1) FROM c "
        "WHERE c.replacement_source_id = @source_id"
    )

    result = list(
        container.query_items(
            query=query,
            parameters=[
                {
                    "name": "@source_id",
                    "value": source_product_id
                }
            ],
            enable_cross_partition_query=True
        )
    )

    return bool(
        result and result[0] > 0
    )


# disconnect ---------------------------------------------

def disconnect_cosmos():
    global client, database, container

    client = None
    database = None
    container = None
